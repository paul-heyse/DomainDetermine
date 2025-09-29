"""High-level ingestion connectors that tie fetchers and parsers together."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from .canonical import SnapshotTables
from .fetchers import CheckedResponse, FetchError, HttpFetcher, SparqlFetcher, build_metadata
from .models import (
    ConnectorContext,
    IngestResult,
    LicensingPolicy,
    ParserOutput,
    SnapshotInfo,
    SourceConfig,
    SourceType,
)
from .normalization import NormalizationPipeline
from .parsers import ParserError, ParserFactory
from .query import SnapshotQueryService
from .telemetry import record_bytes, track_latency
from .validation import KOSValidator

logger = logging.getLogger(__name__)


class IngestConnector:
    """Entry point for executing a single source ingestion."""

    def __init__(
        self,
        context: ConnectorContext,
        http_fetcher: Optional[HttpFetcher] = None,
        sparql_fetcher: Optional[SparqlFetcher] = None,
    ) -> None:
        self.context = context
        self.http_fetcher = http_fetcher or HttpFetcher()
        self.sparql_fetcher = sparql_fetcher or SparqlFetcher()
        self.normalizer = NormalizationPipeline()
        self.validator = KOSValidator()

    def run(self, config: SourceConfig) -> IngestResult:
        """Execute fetch → parse → normalize for a single KOS source."""

        self.context.metrics.incr("runs")
        start = time.time()
        target_dir = self.context.ensure_root() / config.id
        target_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Starting ingest for %s", config.id)

        with track_latency(self.context.metrics, "fetch.duration_seconds"):
            response = self._fetch(config)

        content = response.content
        bytes_downloaded = len(content)
        record_bytes(self.context.metrics, "fetch.bytes", bytes_downloaded)
        checksum = response.checksum() if bytes_downloaded else None

        previous_etag = self._load_previous_metadata(target_dir)
        delta = "changed"
        if previous_etag and previous_etag == response.etag:
            delta = "unchanged"

        metadata = build_metadata(
            config=config,
            context=self.context,
            response=response,
            bytes_downloaded=bytes_downloaded,
            checksum=checksum,
            delta=delta,
        )

        artifact_path = target_dir / config.artifact_basename()
        artifact_path.write_bytes(content)
        metadata.artifact_path = artifact_path

        parser_output: Optional[ParserOutput] = None
        snapshot_info: Optional[SnapshotInfo] = None
        validation_report = None
        if config.type != SourceType.SPARQL:
            with track_latency(self.context.metrics, "normalize.duration_seconds"):
                normalization = self.normalizer.run(config, content)
            parser_output = normalization.parser_output
            tables = normalization.tables
            snapshot_info = self._persist_snapshot(
                config=config,
                target_dir=target_dir,
                tables=tables,
            )
            with track_latency(self.context.metrics, "validation.duration_seconds"):
                validation = self.validator.validate(config, tables, parser_output)
            validation_report = validation
            if snapshot_info:
                snapshot_info.validation_report = validation

        self._persist_metadata(target_dir, metadata)

        duration = time.time() - start
        self.context.metrics.observe("duration_seconds", duration)
        logger.info("Completed ingest for %s in %.2fs", config.id, duration)

        query_service = None
        if snapshot_info:
            query_service = SnapshotQueryService(normalization.tables)

        result = IngestResult(
            config=config,
            metadata=metadata,
            parser_output=parser_output,
            changed=delta == "changed",
            snapshot=snapshot_info,
            query_service=query_service,
        )
        if validation_report:
            metadata.extra["validation"] = validation_report.to_dict()
        return result

    def _fetch(self, config: SourceConfig) -> CheckedResponse:
        """Retrieve bytes from remote/local/endpoint sources with policy awareness."""
        if config.type == SourceType.SPARQL:
            return self.sparql_fetcher.fetch(config, self.context)
        if config.is_remote():
            return self.http_fetcher.fetch(config, self.context)
        logger.debug("Reading local file %s", config.location)
        path = Path(config.location)
        if not path.exists():
            raise FetchError(f"Local source not found: {config.location}")
        content = path.read_bytes()
        return CheckedResponse(content=content, status_code=200, headers={})

    def _parse(self, config: SourceConfig, content: bytes, target_dir: Path) -> ParserOutput:
        """Select and execute the correct parser for the source format."""
        parser = ParserFactory.get_parser(config)
        try:
            return parser.parse(config=config, content=content, target_dir=target_dir)
        except ParserError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ParserError(f"Unexpected parser failure for {config.id}: {exc}") from exc

    def _persist_snapshot(
        self,
        config: SourceConfig,
        target_dir: Path,
        tables: SnapshotTables,
    ) -> SnapshotInfo:
        """Write the snapshot manifest, Parquet tables, and graph exports."""
        snapshot_dir = target_dir / "snapshot"
        table_dir = snapshot_dir / "tables"
        table_paths = tables.to_parquet(table_dir)
        schema_info = tables.table_schemas()
        graph_paths = []
        if config.type == SourceType.SKOS:
            graph_paths.append(str(target_dir / f"{config.id}-graph.ttl"))
        elif config.type == SourceType.OWL:
            graph_paths.append(str(target_dir / f"{config.id}-materialized.owl"))
        elif config.type == SourceType.OBO:
            graph_paths.append(str(target_dir / f"{config.id}-json.json"))
        manifest_path = snapshot_dir / "manifest.json"
        manifest = {
            "snapshot_id": f"{config.id}-{int(time.time())}",
            "sources": [
                {
                    "id": config.id,
                    "type": config.type.value,
                    "location": config.location,
                }
            ],
            "table_paths": {name: str(path) for name, path in table_paths.items()},
            "table_schemas": schema_info,
            "graph_paths": graph_paths,
        }
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        import json

        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        return SnapshotInfo(
            snapshot_id=manifest["snapshot_id"],
            manifest_path=manifest_path,
            tables_dir=table_dir,
            graph_paths=[Path(p) for p in graph_paths],
            table_schemas=schema_info,
        )

    def _persist_metadata(self, target_dir: Path, metadata) -> None:
        """Serialize run metadata for governance and reproducibility."""
        metadata_path = target_dir / "metadata.json"
        data = {
            "source_id": metadata.source_id,
            "source_type": metadata.source_type.value,
            "retrieved_at": metadata.retrieved_at.isoformat(),
            "bytes_downloaded": metadata.bytes_downloaded,
            "checksum": metadata.checksum,
            "etag": metadata.etag,
            "last_modified": metadata.last_modified,
            "delta": metadata.delta,
            "license_name": metadata.license_name,
            "export_allowed": metadata.export_allowed,
            "restricted_fields": list(metadata.restricted_fields),
            "policy_notes": metadata.policy_notes,
            "artifact_path": str(metadata.artifact_path) if metadata.artifact_path else None,
            "fetch_url": metadata.fetch_url,
            "extra": dict(metadata.extra),
        }
        import json

        metadata_path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def _load_previous_metadata(self, target_dir: Path) -> Optional[str]:
        metadata_path = target_dir / "metadata.json"
        if not metadata_path.exists():
            return None
        import json

        try:
            data = json.loads(metadata_path.read_text())
        except json.JSONDecodeError:
            return None
        return data.get("etag")


class ConnectorContextFactory:
    """Utility for constructing connector contexts with default policies."""

    @staticmethod
    def default(artifact_root: Path) -> ConnectorContext:
        policies = {
            "snomed": LicensingPolicy(
                name="SNOMED CT",
                allow_raw_exports=False,
                restricted_fields={"pref_label", "definition"},
                notes="SNOMED CT license prohibits redistribution of raw terms.",
            )
        }
        return ConnectorContext(artifact_root=artifact_root, policies=policies)
