"""Crosswalk proposal utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol, Sequence

from .models import CrosswalkProposal, DecisionMethod, MappingRecord


@dataclass(slots=True)
class CrosswalkAlignment:
    """Represents alignment evidence surfaced by an external system."""

    target_scheme: str
    target_concept_id: str
    lexical_score: float
    semantic_score: float
    rationale: str


class CrosswalkEvidenceProvider(Protocol):
    """Protocol describing crosswalk evidence retrieval."""

    def align(self, concept_id: str, *, metadata: Mapping[str, str]) -> Sequence[CrosswalkAlignment]:  # pragma: no cover - protocol
        ...


@dataclass(slots=True)
class CrosswalkProposer:
    """Generates cross-scheme alignment proposals."""

    target_schemes: Sequence[str]
    threshold: float = 0.6
    evidence_provider: CrosswalkEvidenceProvider | None = None

    def propose(self, records: Iterable[MappingRecord]) -> tuple[CrosswalkProposal, ...]:
        proposals: list[CrosswalkProposal] = []
        for record in records:
            lexical_overlap = float(record.method_metadata.get("lexical_overlap", 0.0))
            semantic_overlap = float(record.method_metadata.get("semantic_overlap", 0.0))
            combined = max(lexical_overlap, semantic_overlap)
            if combined < self.threshold:
                continue
            evidence_quotes = tuple(record.evidence_quotes)
            proposer = (
                DecisionMethod.LLM if record.decision_method is DecisionMethod.LLM else DecisionMethod.HEURISTIC
            )
            if self.evidence_provider:
                alignments = self.evidence_provider.align(record.concept_id, metadata=record.method_metadata)
                for alignment in alignments:
                    if max(alignment.lexical_score, alignment.semantic_score) < self.threshold:
                        continue
                    proposals.append(
                        CrosswalkProposal(
                            source_concept_id=record.concept_id,
                            target_scheme=alignment.target_scheme,
                            target_concept_id=alignment.target_concept_id,
                            relation="exactMatch" if alignment.semantic_score >= 0.8 else "closeMatch",
                            lexical_score=alignment.lexical_score,
                            semantic_score=alignment.semantic_score,
                            llm_rationale=alignment.rationale,
                            evidence_quotes=evidence_quotes,
                            proposer=proposer,
                            kos_snapshot_id=record.kos_snapshot_id,
                        )
                    )
                continue
            for scheme in self.target_schemes:
                proposals.append(
                    CrosswalkProposal(
                        source_concept_id=record.concept_id,
                        target_scheme=scheme,
                        target_concept_id=record.concept_id,
                        relation="exactMatch" if combined >= 0.9 else "closeMatch",
                        lexical_score=lexical_overlap,
                        semantic_score=semantic_overlap,
                        llm_rationale="Derived from mapping evidence",
                        evidence_quotes=evidence_quotes,
                        proposer=proposer,
                        kos_snapshot_id=record.kos_snapshot_id,
                    )
                )
        return tuple(proposals)

