"""Crosswalk proposal utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .models import CrosswalkProposal, DecisionMethod, MappingRecord


@dataclass(slots=True)
class CrosswalkProposer:
    """Generates cross-scheme alignment proposals."""

    target_schemes: Sequence[str]
    threshold: float = 0.6

    def propose(self, records: Iterable[MappingRecord]) -> tuple[CrosswalkProposal, ...]:
        proposals: list[CrosswalkProposal] = []
        for record in records:
            if record.method_metadata.get("lexical_overlap", 0.0) < self.threshold:
                continue
            for scheme in self.target_schemes:
                proposals.append(
                    CrosswalkProposal(
                        source_concept_id=record.concept_id,
                        target_scheme=scheme,
                        target_concept_id=record.concept_id,
                        relation="exactMatch",
                        lexical_score=1.0,
                        semantic_score=1.0,
                        llm_rationale="Placeholder rationale",
                        evidence_quotes=record.evidence_quotes,
                        proposer=DecisionMethod.HEURISTIC,
                        kos_snapshot_id=record.kos_snapshot_id,
                    )
                )
        return tuple(proposals)

