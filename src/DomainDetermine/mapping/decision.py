"""Decision engines for mapping pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from .models import Candidate, CandidateLogEntry, DecisionMethod, MappingItem, MappingRecord


class DecisionEngine:
    """Abstract decision engine interface."""

    def __init__(self, confidence_threshold: float = 0.0) -> None:
        self.confidence_threshold = confidence_threshold
        self.allow_ties_for_review = True

    def decide(
        self,
        mapping_item: MappingItem,
        ranked_candidates: Sequence[Candidate],
        llm_response: Optional[dict[str, str]] = None,
    ) -> Optional[MappingRecord]:
        raise NotImplementedError

    def build_candidate_log(
        self,
        mapping_item: MappingItem,
        ranked_candidates: Sequence[Candidate],
        decision: Optional[MappingRecord],
    ) -> CandidateLogEntry:
        decision_method = decision.decision_method if decision else DecisionMethod.HEURISTIC
        return CandidateLogEntry(
            mapping_item=mapping_item,
            candidates=ranked_candidates,
            final_concept_id=decision.concept_id if decision else None,
            decision_method=decision_method,
        )


@dataclass(slots=True)
class HeuristicDecisionEngine(DecisionEngine):
    """Heuristic fallback decision engine."""

    def decide(
        self,
        mapping_item: MappingItem,
        ranked_candidates: Sequence[Candidate],
    ) -> Optional[MappingRecord]:
        if not ranked_candidates:
            return None
        top_candidate = ranked_candidates[0]
        if top_candidate.score < self.confidence_threshold:
            return None
        return MappingRecord(
            mapping_item=mapping_item,
            concept_id=top_candidate.concept_id,
            confidence=top_candidate.score,
            decision_method=DecisionMethod.HEURISTIC,
            evidence_quotes=(
                f"Selected {top_candidate.concept_id} via heuristic threshold {self.confidence_threshold}",
            ),
            method_metadata={"note": "heuristic decision"},
            kos_snapshot_id="unknown",
            coverage_plan_id=mapping_item.context.coverage_plan_slice_id,
        )


@dataclass(slots=True)
class LLMDecisionEngine(DecisionEngine):
    """LLM gated decision engine stub."""

    model_ref: str
    llm_callable: Callable[[str], dict[str, str]]
    human_review_queue: list[MappingItem] = field(default_factory=list)
    confidence_threshold: float = 0.0
    tie_threshold: float = 0.05

    def __post_init__(self) -> None:
        DecisionEngine.__init__(self, confidence_threshold=self.confidence_threshold)

    def decide(
        self,
        mapping_item: MappingItem,
        ranked_candidates: Sequence[Candidate],
        llm_response: Optional[dict[str, str]] = None,
    ) -> Optional[MappingRecord]:
        if not ranked_candidates:
            return None
        deliberation = llm_response or self._prompt_llm(mapping_item, ranked_candidates)
        selected_id = deliberation.get("concept_id")
        confidence = float(deliberation.get("confidence", "0"))
        if selected_id not in {candidate.concept_id for candidate in ranked_candidates}:
            return None
        if confidence < self.confidence_threshold:
            self.human_review_queue.append(mapping_item)
            return None
        if self.allow_ties_for_review and len(ranked_candidates) >= 2:
            delta = abs(ranked_candidates[0].score - ranked_candidates[1].score)
            if delta <= self.tie_threshold:
                self.human_review_queue.append(mapping_item)
                return None
        evidence_payload = deliberation.get("evidence", [])
        if isinstance(evidence_payload, str):
            evidence_payload = json.loads(evidence_payload)
        evidence = tuple(evidence_payload)
        method_metadata = {
            "model_ref": self.model_ref,
            "prompt_hash": deliberation.get("prompt_hash", ""),
            "raw": json.dumps(deliberation, ensure_ascii=False),
        }
        reason = deliberation.get("reason")
        if reason:
            method_metadata["reason"] = reason
        latency_ms = float(deliberation.get("latency_ms", 0.0)) if "latency_ms" in deliberation else None
        cost_usd = float(deliberation.get("cost_usd", 0.0)) if "cost_usd" in deliberation else None
        reason_code = deliberation.get("reason_code")
        record = MappingRecord(
            mapping_item=mapping_item,
            concept_id=selected_id,
            confidence=confidence,
            decision_method=DecisionMethod.LLM,
            evidence_quotes=evidence,
            method_metadata=method_metadata,
            kos_snapshot_id="unknown",
            coverage_plan_id=mapping_item.context.coverage_plan_slice_id,
            llm_model_ref=self.model_ref,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            reason_code=reason_code,
        )
        return record

    def _prompt_llm(
        self,
        mapping_item: MappingItem,
        ranked_candidates: Sequence[Candidate],
    ) -> dict[str, str]:
        payload = {
            "item": mapping_item.source_text,
            "context": mapping_item.context.facets,
            "candidates": [candidate.concept_id for candidate in ranked_candidates],
        }
        response = self.llm_callable(json.dumps(payload))
        return response

