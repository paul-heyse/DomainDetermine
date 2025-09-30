"""Persistence layer for mapping artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable

try:
    import duckdb
except ModuleNotFoundError:  # pragma: no cover
    duckdb = None  # type: ignore[assignment]

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ModuleNotFoundError:  # pragma: no cover
    pa = None  # type: ignore[assignment]
    pq = None  # type: ignore[assignment]

from .models import MappingBatchResult


@dataclass(slots=True)
class MappingStorage:
    """Handles persistence of mapping outputs to Parquet and DuckDB."""

    output_root: Path
    duckdb_path: Path
    manifest_log_path: Path | None = None
    _conn: object = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._conn = self._connect_duckdb()
        self._initialize_duckdb()

    def _connect_duckdb(self):
        if duckdb is None:
            raise RuntimeError("duckdb dependency is required for MappingStorage")
        return duckdb.connect(str(self.duckdb_path))

    def _initialize_duckdb(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mapping_records (
                concept_id TEXT,
                confidence DOUBLE,
                decision_method TEXT,
                evidence_quotes TEXT,
                kos_snapshot_id TEXT,
                coverage_plan_id TEXT,
                llm_model_ref TEXT,
                latency_ms DOUBLE,
                cost_usd DOUBLE,
                reason_code TEXT,
                created_at TIMESTAMP,
                source_text TEXT
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidate_logs (
                mapping_source TEXT,
                final_concept_id TEXT,
                decision_method TEXT,
                candidates JSON
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS crosswalk_proposals (
                source_concept_id TEXT,
                target_scheme TEXT,
                target_concept_id TEXT,
                relation TEXT,
                lexical_score DOUBLE,
                semantic_score DOUBLE,
                rationale TEXT,
                kos_snapshot_id TEXT,
                status TEXT
            )
            """
        )

    def persist_batch(self, batch: MappingBatchResult) -> None:
        self._write_parquet(batch.records, "mapping_records.parquet")
        self._write_parquet(batch.candidate_logs, "candidate_logs.parquet")
        self._write_parquet(batch.crosswalk_proposals, "crosswalk_proposals.parquet")
        self._write_metrics(batch)
        self._append_duckdb(batch)

    def _write_parquet(self, objects: Iterable[object], filename: str) -> None:
        if pa is None or pq is None:
            raise RuntimeError("pyarrow dependency is required for MappingStorage")
        serialised_rows = []
        for obj in objects:
            row = {}
            for key, value in asdict(obj).items():
                row[key] = self._normalise_value(value)
            serialised_rows.append(row)
        table = pa.Table.from_pylist(serialised_rows)
        pq.write_table(table, self.output_root / filename)

    @staticmethod
    def _normalise_value(value):
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, (list, tuple)):
            return [MappingStorage._normalise_value(v) for v in value]
        if isinstance(value, dict):
            normalised = {k: MappingStorage._normalise_value(v) for k, v in value.items()}
            return json.dumps(normalised, ensure_ascii=False)
        if isinstance(value, set):
            return [MappingStorage._normalise_value(v) for v in sorted(value)]
        return value

    def _write_metrics(self, batch: MappingBatchResult) -> None:
        path = self.output_root / "metrics.json"
        path.write_text(json.dumps(batch.metrics, indent=2, sort_keys=True))

    def _append_duckdb(self, batch: MappingBatchResult) -> None:
        for record in batch.records:
            self._conn.execute(
                """
                INSERT INTO mapping_records (
                    concept_id,
                    confidence,
                    decision_method,
                    evidence_quotes,
                    kos_snapshot_id,
                    coverage_plan_id,
                    llm_model_ref,
                    latency_ms,
                    cost_usd,
                    reason_code,
                    created_at,
                    source_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.concept_id,
                    record.confidence,
                    record.decision_method.value,
                    json.dumps(record.evidence_quotes),
                    record.kos_snapshot_id,
                    record.coverage_plan_id,
                    record.llm_model_ref,
                    record.latency_ms,
                    record.cost_usd,
                    record.reason_code,
                    record.created_at,
                    record.mapping_item.source_text,
                ),
            )
        for log in batch.candidate_logs:
            candidates_payload = [
                {
                    "concept_id": candidate.concept_id,
                    "score": candidate.score,
                    "source": candidate.source.value if hasattr(candidate.source, "value") else candidate.source,
                }
                for candidate in log.candidates
            ]
            self._conn.execute(
                """
                INSERT INTO candidate_logs VALUES (?, ?, ?, ?)
                """,
                (
                    log.mapping_item.source_text,
                    log.final_concept_id,
                    log.decision_method.value,
                    json.dumps(candidates_payload),
                ),
            )
        for proposal in batch.crosswalk_proposals:
            self._conn.execute(
                """
                INSERT INTO crosswalk_proposals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.source_concept_id,
                    proposal.target_scheme,
                    proposal.target_concept_id,
                    proposal.relation,
                    proposal.lexical_score,
                    proposal.semantic_score,
                    proposal.llm_rationale,
                    proposal.kos_snapshot_id,
                    proposal.status,
                ),
            )

    def close(self) -> None:
        self._conn.close()

