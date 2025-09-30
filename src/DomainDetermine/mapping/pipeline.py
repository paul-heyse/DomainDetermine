"""Mapping pipeline assembly."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from DomainDetermine.llm import SchemaRegistry, TritonLLMProvider
from DomainDetermine.mapping.persistence import MappingManifestWriter

from .candidate_generation import CandidateGenerator
from .crosswalk import CrosswalkProposer
from .decision import DecisionEngine
from .models import (
    Candidate,
    CandidateLogEntry,
    MappingBatchResult,
    MappingContext,
    MappingItem,
    MappingRecord,
    MappingReviewQueueEntry,
)
from .normalization import TextNormalizer
from .scoring import CandidateScorer
from .telemetry import MappingTelemetry


@dataclass(slots=True)
class MappingPipeline:
    """Coordinates the mapping workflow."""

    normalizer: TextNormalizer
    generator: CandidateGenerator
    scorer: CandidateScorer
    decision_engine: DecisionEngine
    crosswalk_proposer: CrosswalkProposer
    llm_provider: TritonLLMProvider
    schema_registry: SchemaRegistry
    cross_encoder_model: str | None = None
    telemetry: MappingTelemetry | None = None
    kos_snapshot_id: str = "unknown"
    manifest_writer: MappingManifestWriter | None = None
    mapping_run_id: str | None = None
    review_queue: list[MappingReviewQueueEntry] = field(default_factory=list)

    def run(self, items: Iterable[MappingItem]) -> MappingBatchResult:
        """Execute normalize → generate → score → decide flow for mapping items."""

        records: list[MappingRecord] = []
        candidate_logs: list[CandidateLogEntry] = []
        schema_record = self.schema_registry.load_record("mapping_decision", "v1")
        schema = schema_record.schema
        for item in items:
            normalized = self.normalizer.normalize(item.source_text)
            context = self._merge_context_language(item.context, normalized.language)
            candidates = self.generator.generate(normalized.normalized, context)
            ranked_candidates = self.scorer.score(candidates)
            if self.cross_encoder_model and ranked_candidates:
                ce_scores = self._cross_encoder_scores(item, ranked_candidates)
                ranked_candidates = self.scorer.rerank(ranked_candidates, ce_scores)
            llm_payload = {
                "item": item.source_text,
                "candidates": [candidate.concept_id for candidate in ranked_candidates],
                "context": context.facets,
            }
            try:
                llm_response = self.llm_provider.generate_json(
                    schema,
                    json.dumps(llm_payload),
                    schema_id=schema_record.id,
                )
            except Exception:  # pragma: no cover - defensive fallback
                self.review_queue.append(
                    MappingReviewQueueEntry(
                        item=item,
                        reason="llm_error",
                        reason_code=self.decision_engine.review_reason_codes.get("llm_error"),
                    )
                )
                continue
            decision = self.decision_engine.decide(item, ranked_candidates, llm_response)
            log_entry = self.decision_engine.build_candidate_log(item, ranked_candidates, decision)
            candidate_logs.append(log_entry)
            if decision:
                decision.kos_snapshot_id = self.kos_snapshot_id
                records.append(decision)
            else:
                reason = item.metadata.get("review_reason") if item.metadata else None
                reason_code = item.metadata.get("review_reason_code") if item.metadata else None
                self.review_queue.append(
                    MappingReviewQueueEntry(
                        item=item,
                        reason=reason or "requires_review",
                        reason_code=reason_code,
                    )
                )
        proposals = self.crosswalk_proposer.propose(records)
        pos_candidates = sum(1 for log in candidate_logs if log.final_concept_id)
        metrics = self._compute_metrics(records, candidate_logs)
        metrics["avg_candidate_count"] = pos_candidates / len(candidate_logs) if candidate_logs else 0.0
        if self.telemetry:
            self.telemetry.emit_metrics(metrics)
        batch = MappingBatchResult(
            records=tuple(records),
            candidate_logs=tuple(candidate_logs),
            crosswalk_proposals=proposals,
            metrics=metrics,
        )
        if self.manifest_writer:
            manifest = self.manifest_writer.write_batch(
                mapping_run_id=self.mapping_run_id or schema_record.id,
                kos_snapshot_id=self.kos_snapshot_id,
                batch=batch,
            )
        return batch

    def _cross_encoder_scores(
        self,
        item: MappingItem,
        candidates: Sequence[Candidate],
    ) -> Sequence[float]:
        payload = {
            "item": item.source_text,
            "candidates": [candidate.concept_id for candidate in candidates],
            "mode": "rerank",
        }
        response = self.llm_provider.rank_candidates(payload)
        return [float(score) for score in response.get("scores", [])]

    @staticmethod
    def _merge_context_language(context: MappingContext, language: str) -> MappingContext:
        if context.language:
            return context
        return MappingContext(
            domain=context.domain,
            jurisdiction=context.jurisdiction,
            language=language,
            coverage_plan_slice_id=context.coverage_plan_slice_id,
            facets=context.facets,
        )

    @staticmethod
    def _compute_metrics(
        records: Sequence[MappingRecord],
        candidate_logs: Sequence[CandidateLogEntry],
    ) -> dict[str, float]:
        total = len(candidate_logs)
        resolved = len(records)
        return {
            "items_total": float(total),
            "items_resolved": float(resolved),
            "resolution_rate": float(resolved / total) if total else 0.0,
        }

