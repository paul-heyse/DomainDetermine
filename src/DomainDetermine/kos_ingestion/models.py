"""Data models for KOS ingestion connectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Mapping, MutableMapping, Optional, Sequence, Set

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    """Supported input source types for KOS ingestion."""

    SKOS = "skos"
    OWL = "owl"
    OBO = "obo"
    SPARQL = "sparql"


class DeltaStrategy(str, Enum):
    """Strategies for determining whether content has changed."""

    ETAG = "etag"
    LAST_MODIFIED = "last-modified"
    CHECKSUM = "checksum"


class ExportMode(str, Enum):
    """Controls how connectors materialise artifacts under licensing rules."""

    FULL = "full"
    REDACTED = "redacted"
    METADATA_ONLY = "metadata-only"


@dataclass(frozen=True)
class LicensingPolicy:
    """Represents licensing rules that apply to a source."""

    name: str
    allow_raw_exports: bool = True
    restricted_fields: Set[str] = field(default_factory=set)
    notes: Optional[str] = None

    def export_allowed(self) -> bool:
        """Return True when raw identifier/label exports are permitted."""

        return self.allow_raw_exports

    def requires_masking(self, field_name: str) -> bool:
        """Return True when a field must be masked under this policy."""

        if self.allow_raw_exports:
            return False
        if not self.restricted_fields:
            return True
        return field_name in self.restricted_fields


@dataclass(frozen=True)
class SourceConfig:
    """Configuration describing how to obtain a KOS source."""

    id: str
    type: SourceType
    location: str
    format: Optional[str] = None
    license_name: str = "default"
    headers: Mapping[str, str] = field(default_factory=dict)
    auth: Optional[Mapping[str, str]] = None
    credential_secret: Optional[str] = None
    sparql_query: Optional[str] = None
    timeout_seconds: int = 30
    sparql_max_rows: int = 5000
    sparql_page_size: int = 1000
    verify_tls: bool = True
    max_bytes: Optional[int] = None
    resume_download: bool = False
    rate_limit_per_second: Optional[float] = None
    retry_limit: int = 3
    backoff_seconds: float = 2.0
    cache_ttl_seconds: Optional[int] = None
    delta_strategy: DeltaStrategy = DeltaStrategy.ETAG
    export_mode: ExportMode = ExportMode.FULL

    def is_remote(self) -> bool:
        """Return True if the source location refers to a remote resource."""

        return self.location.startswith("http://") or self.location.startswith("https://")

    def artifact_basename(self) -> str:
        """Return a filesystem-friendly base name for snapshot artifacts."""

        suffix = {
            SourceType.SKOS: "ttl",
            SourceType.OWL: "owl",
            SourceType.OBO: "obo",
            SourceType.SPARQL: "json",
        }[self.type]
        return f"{self.id}.{suffix}"

    def auth_headers(self, context: "ConnectorContext") -> Mapping[str, str]:
        """Resolve authentication headers using inline config or secrets."""

        resolved: Dict[str, str] = dict(self.auth or {})
        if self.credential_secret and context.secret_resolver:
            secret_headers = context.secret_resolver(self.credential_secret)
            resolved.update(secret_headers)
        return resolved


@dataclass
class ConnectorMetadata:
    """Metadata emitted by a connector for reproducibility and auditing."""

    source_id: str
    source_type: SourceType
    retrieved_at: datetime
    bytes_downloaded: int
    checksum: Optional[str]
    etag: Optional[str]
    last_modified: Optional[str]
    delta: str
    license_name: str
    export_allowed: bool
    restricted_fields: Sequence[str] = field(default_factory=tuple)
    policy_notes: Optional[str] = None
    artifact_path: Optional[Path] = None
    fetch_url: Optional[str] = None
    extra: MutableMapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "retrieved_at": self.retrieved_at.isoformat(),
            "bytes_downloaded": self.bytes_downloaded,
            "checksum": self.checksum,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "delta": self.delta,
            "license_name": self.license_name,
            "export_allowed": self.export_allowed,
            "restricted_fields": list(self.restricted_fields),
            "policy_notes": self.policy_notes,
            "artifact_path": str(self.artifact_path) if self.artifact_path else None,
            "fetch_url": self.fetch_url,
            "extra": dict(self.extra),
        }


@dataclass
class ParserOutput:
    """Structured result emitted by a parser."""

    stats: Mapping[str, int]
    warnings: Sequence[str] = field(default_factory=tuple)
    materialized_graph_path: Optional[Path] = None
    extras: Mapping[str, object] = field(default_factory=dict)


class SnapshotValidationSummary(BaseModel):
    shacl: Mapping[str, object]
    tabular: Mapping[str, object]


class SnapshotManifestModel(BaseModel):
    snapshot_id: str
    created_at: datetime
    sources: Sequence[Mapping[str, str]]
    table_hashes: Mapping[str, str]
    graph_paths: Sequence[str]
    license_notes: Sequence[str]
    validation_report: SnapshotValidationSummary


class SnapshotInfo(BaseModel):
    """Metadata describing a persisted snapshot."""

    snapshot_id: str
    manifest_path: Path
    tables_dir: Path
    graph_paths: Sequence[Path]
    table_schemas: Mapping[str, Mapping[str, str]] = Field(default_factory=dict)
    validation_report: Optional[SnapshotValidationSummary] = None

    @field_validator("graph_paths", mode="before")
    @classmethod
    def ensure_paths(cls, value):
        return [Path(item) for item in value]


@dataclass
class IngestResult:
    """Top-level result returned by an ingest connector."""

    config: SourceConfig
    metadata: ConnectorMetadata
    parser_output: Optional[ParserOutput]
    changed: bool
    snapshot: Optional[SnapshotInfo] = None
    query_service: Optional[object] = None


@dataclass
class ConnectorMetrics:
    """Simple in-memory metrics accumulator for connector runs."""

    counters: MutableMapping[str, int] = field(default_factory=dict)
    timings: MutableMapping[str, list] = field(default_factory=dict)

    def incr(self, key: str, amount: int = 1) -> None:
        self.counters[key] = self.counters.get(key, 0) + amount

    def observe(self, key: str, value: float) -> None:
        bucket = self.timings.setdefault(key, [])
        bucket.append(value)

    def as_dict(self) -> Dict[str, object]:
        return {
            "counters": dict(self.counters),
            "timings": {k: list(v) for k, v in self.timings.items()},
        }


@dataclass
class ConnectorContext:
    """Runtime context shared by connector executions."""

    artifact_root: Path
    policies: Mapping[str, LicensingPolicy] = field(default_factory=dict)
    metrics: ConnectorMetrics = field(default_factory=ConnectorMetrics)
    secret_resolver: Optional[Callable[[str], Mapping[str, str]]] = None
    rate_limit_state: MutableMapping[str, float] = field(default_factory=dict)

    def resolve_policy(self, license_name: str) -> LicensingPolicy:
        return self.policies.get(license_name, LicensingPolicy(name=license_name or "default"))

    def ensure_root(self) -> Path:
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        return self.artifact_root

    def throttle_key(self, config: SourceConfig) -> str:
        return f"{config.type}:{config.location}"
