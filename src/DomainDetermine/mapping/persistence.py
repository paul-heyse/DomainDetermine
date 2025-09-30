"""Persistence helpers for mapping outcomes and crosswalk manifests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from .models import CandidateLogEntry, CrosswalkProposal, MappingBatchResult, MappingRecord


@dataclass(slots=True)
class MappingManifestWriter:
    """Writes mapping run manifests for governance and replay."""

    output_dir: Path

    def write(
        self,
        *,
        mapping_run_id: str,
        kos_snapshot_id: str,
        records: Sequence[MappingRecord],
        crosswalks: Sequence[CrosswalkProposal],
        candidate_logs: Sequence[CandidateLogEntry],
        metrics: Mapping[str, float],
    ) -> Path:
        timestamp = datetime.now(timezone.utc).isoformat()
        manifest = {
            "mapping_run_id": mapping_run_id,
            "kos_snapshot_id": kos_snapshot_id,
            "generated_at": timestamp,
            "record_count": len(records),
            "records": [self._record_payload(record) for record in records],
            "crosswalks": [self._crosswalk_payload(proposal) for proposal in crosswalks],
            "candidate_logs": [self._candidate_payload(log) for log in candidate_logs],
            "metrics": dict(metrics),
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"mapping_manifest_{mapping_run_id}.json"
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_batch(
        self,
        *,
        mapping_run_id: str,
        kos_snapshot_id: str,
        batch: MappingBatchResult,
    ) -> Path:
        return self.write(
            mapping_run_id=mapping_run_id,
            kos_snapshot_id=kos_snapshot_id,
            records=batch.records,
            crosswalks=batch.crosswalk_proposals,
            candidate_logs=batch.candidate_logs,
            metrics=batch.metrics,
        )

    @staticmethod
    def _record_payload(record: MappingRecord) -> Mapping[str, object]:
        return {
            "source_text": record.mapping_item.source_text,
            "concept_id": record.concept_id,
            "confidence": record.confidence,
            "decision_method": record.decision_method.value,
            "evidence": list(record.evidence_quotes),
            "method_metadata": dict(record.method_metadata),
            "coverage_plan_id": record.coverage_plan_id,
            "kos_snapshot_id": record.kos_snapshot_id,
            "created_at": record.created_at.isoformat(),
            "llm_model_ref": record.llm_model_ref,
            "latency_ms": record.latency_ms,
            "cost_usd": record.cost_usd,
            "reason_code": record.reason_code,
        }

    @staticmethod
    def _crosswalk_payload(proposal: CrosswalkProposal) -> Mapping[str, object]:
        return {
            "source_concept_id": proposal.source_concept_id,
            "target_scheme": proposal.target_scheme,
            "target_concept_id": proposal.target_concept_id,
            "relation": proposal.relation,
            "lexical_score": proposal.lexical_score,
            "semantic_score": proposal.semantic_score,
            "llm_rationale": proposal.llm_rationale,
            "evidence_quotes": list(proposal.evidence_quotes),
            "proposer": proposal.proposer.value,
            "kos_snapshot_id": proposal.kos_snapshot_id,
            "status": proposal.status,
            "reviewer": proposal.reviewer,
            "reviewed_at": proposal.reviewed_at.isoformat() if proposal.reviewed_at else None,
        }

    @staticmethod
    def _candidate_payload(log: CandidateLogEntry) -> Mapping[str, object]:
        return {
            "source_text": log.mapping_item.source_text,
            "decision_method": log.decision_method.value,
            "final_concept_id": log.final_concept_id,
            "candidates": [
                {
                    "concept_id": candidate.concept_id,
                    "label": candidate.label,
                    "score": candidate.score,
                    "source": candidate.source.value,
                }
                for candidate in log.candidates
            ],
        }


__all__ = ["MappingManifestWriter"]
