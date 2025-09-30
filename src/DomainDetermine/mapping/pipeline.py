"""Mapping pipeline assembly."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from DomainDetermine.llm import SchemaRegistry, TritonLLMProvider
from DomainDetermine.mapping.persistence import MappingManifestWriter

from .candidate_generation import CandidateGenerator
from .crosswalk import CrosswalkProposer
from .decision import DecisionEngine
from .models import (
    Candidate,
    CandidateSource,
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

        items_list = list(items)
        records: list[MappingRecord] = []
        candidate_logs: list[CandidateLogEntry] = []
        schema_record = self.schema_registry.load_record("mapping_decision", "v1")
        schema = schema_record.schema
        queue_initial_size = len(self.review_queue)
        for item in items_list:
            normalized = self.normalizer.normalize(item.source_text)
            context = self._merge_context_language(item.context, normalized.language)
            candidates = self.generator.generate(normalized.normalized, context)
            ranked_candidates = self.scorer.score(candidates)
            self._record_candidate_metadata(ranked_candidates)
            if self.cross_encoder_model and ranked_candidates:
                ce_scores = self._cross_encoder_scores(item, ranked_candidates)
                ranked_candidates = self.scorer.rerank(ranked_candidates, ce_scores)
                self._record_cross_encoder_metadata(ranked_candidates, ce_scores)
            llm_payload = {
                "item": item.source_text,
                "candidates": [candidate.concept_id for candidate in ranked_candidates],
                "context": context.facets,
                "language": context.language or normalized.language,
                "scores": [candidate.score for candidate in ranked_candidates],
            }
            llm_response = self.llm_provider.generate_json(
                schema,
                json.dumps(llm_payload),
                schema_id=schema_record.id,
            )
            decision = self.decision_engine.decide(item, ranked_candidates, llm_response)
            log_entry = self.decision_engine.build_candidate_log(item, ranked_candidates, decision)
            log_entry.candidate_sources = tuple(candidate.source.value for candidate in ranked_candidates)
            candidate_logs.append(log_entry)
            if decision:
                decision.kos_snapshot_id = self.kos_snapshot_id
                decision.method_metadata = {
                    **decision.method_metadata,
                    "lexical_overlap": f"{self._overlap_score(ranked_candidates, CandidateSource.LEXICAL):.3f}",
                    "semantic_overlap": f"{self._overlap_score(ranked_candidates, CandidateSource.SEMANTIC):.3f}",
                }
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
        deferral_count = float(max(len(self.review_queue) - queue_initial_size, 0))
        metrics = self._compute_metrics(items_list, candidate_logs, records, deferral_count)
        if self.telemetry:
            self.telemetry.emit_metrics(metrics)
        batch = MappingBatchResult(
            records=tuple(records),
            candidate_logs=tuple(candidate_logs),
            crosswalk_proposals=proposals,
            metrics=metrics,
        )
        if self.manifest_writer:
            self.manifest_writer.write_batch(
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
            "candidate_labels": [candidate.label for candidate in candidates],
            "candidate_ids": [candidate.concept_id for candidate in candidates],
        }
        response = self.llm_provider.rank_candidates(payload)
        scores = response.get("scores")
        if scores is None:
            return [candidate.score for candidate in candidates]
        return scores

    def _merge_context_language(self, context: MappingContext, detected_language: str) -> MappingContext:
        if context.language:
            return context
        return MappingContext(
            domain=context.domain,
            jurisdiction=context.jurisdiction,
            language=detected_language,
            coverage_plan_slice_id=context.coverage_plan_slice_id,
            facets=context.facets,
            allowed_concept_ids=context.allowed_concept_ids,
        )

    def _compute_metrics(
        self,
        items: Sequence[MappingItem],
        candidate_logs: Sequence[CandidateLogEntry],
        records: Sequence[MappingRecord],
        deferred_count: float,
    ) -> Mapping[str, float]:
        items_total = float(len(items))
        resolved = float(len(records))
        deferrals = deferred_count
        precision = self._precision_at_1(candidate_logs)
        recall = self._recall_at_k(candidate_logs)
        avg_candidates = (
            sum(len(entry.candidates) for entry in candidate_logs) / len(candidate_logs)
            if candidate_logs
            else 0.0
        )
        return {
            "items_total": items_total,
            "items_resolved": resolved,
            "items_deferred": deferrals,
            "precision_at_1": precision,
            "recall_at_k": recall,
            "avg_candidate_count": avg_candidates,
        }

    @staticmethod
    def _precision_at_1(candidate_logs: Sequence[CandidateLogEntry]) -> float:
        if not candidate_logs:
            return 0.0
        hits = 0
        for log in candidate_logs:
            if not log.final_concept_id:
                continue
            top_candidate = log.candidates[0] if log.candidates else None
            if top_candidate and top_candidate.concept_id == log.final_concept_id:
                hits += 1
        return hits / len(candidate_logs)

    @staticmethod
    def _recall_at_k(candidate_logs: Sequence[CandidateLogEntry], k: int = 5) -> float:
        if not candidate_logs:
            return 0.0
        hits = 0
        for log in candidate_logs:
            top_k = log.candidates[:k]
            if log.final_concept_id and any(candidate.concept_id == log.final_concept_id for candidate in top_k):
                hits += 1
        return hits / len(candidate_logs)

    @staticmethod
    def _overlap_score(candidates: Sequence[Candidate], source: CandidateSource) -> float:
        for candidate in candidates:
            if candidate.source is source:
                return candidate.score
        return 0.0

    @staticmethod
    def _record_candidate_metadata(candidates: Sequence[Candidate]) -> None:
        for candidate in candidates:
            if hasattr(candidate, "metadata"):
                candidate.metadata = {
                    **candidate.metadata,
                    "source": candidate.source.value if hasattr(candidate.source, "value") else str(candidate.source),
                }

    @staticmethod
    def _record_cross_encoder_metadata(candidates: Sequence[Candidate], scores: Sequence[float]) -> None:
        for candidate, score in zip(candidates, scores, strict=False):
            if hasattr(candidate, "metadata"):
                candidate.metadata = {
                    **candidate.metadata,
                    "cross_encoder_score": f"{float(score):.3f}",
                }

