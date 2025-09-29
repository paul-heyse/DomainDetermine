"""Mapping pipeline assembly."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Sequence

from DomainDetermine.llm import SchemaRegistry, TritonLLMProvider

from .candidate_generation import CandidateGenerator
from .crosswalk import CrosswalkProposer
from .decision import DecisionEngine
from .models import (
    CandidateLogEntry,
    MappingBatchResult,
    MappingContext,
    MappingItem,
    MappingRecord,
)
from .normalization import TextNormalizer
from .scoring import CandidateScorer


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

    def run(self, items: Iterable[MappingItem]) -> MappingBatchResult:
        """Execute normalize → generate → score → decide flow for mapping items."""

        records: list[MappingRecord] = []
        candidate_logs: list[CandidateLogEntry] = []
        schema = self.schema_registry.load("mapping_decision", "v1")
        for item in items:
            normalized = self.normalizer.normalize(item.source_text)
            context = self._merge_context_language(item.context, normalized.language)
            candidates = self.generator.generate(normalized.normalized, context)
            ranked_candidates = self.scorer.score(candidates)
            llm_payload = {
                "item": item.source_text,
                "candidates": [candidate.concept_id for candidate in ranked_candidates],
                "context": context.facets,
            }
            llm_response = self.llm_provider.generate_json(schema, json.dumps(llm_payload))
            decision = self.decision_engine.decide(item, ranked_candidates, llm_response)
            log_entry = self.decision_engine.build_candidate_log(item, ranked_candidates, decision)
            candidate_logs.append(log_entry)
            if decision:
                records.append(decision)
        proposals = self.crosswalk_proposer.propose(records)
        metrics = self._compute_metrics(records, candidate_logs)
        return MappingBatchResult(
            records=tuple(records),
            candidate_logs=tuple(candidate_logs),
            crosswalk_proposals=proposals,
            metrics=metrics,
        )

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

