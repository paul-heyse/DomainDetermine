"""Candidate generator for mapping pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .models import Candidate, CandidateSource, ConceptEntry, MappingContext
from .repository import ConceptRepository


@dataclass(slots=True)
class CandidateGenerator:
    """Generates mapping candidates from repository lookups."""

    repository: ConceptRepository

    def generate(self, normalized_text: str, context: MappingContext) -> Sequence[Candidate]:
        candidates: list[Candidate] = []
        entries = self.repository.list_candidates(context)
        for concept in entries:
            score = self._lexical_score(normalized_text, concept)
            candidates.append(
                Candidate(
                    concept_id=concept.concept_id,
                    label=concept.pref_label,
                    source=CandidateSource.LEXICAL,
                    score=score,
                    evidence=concept.definition,
                    language=concept.language,
                )
            )
        return candidates

    @staticmethod
    def _lexical_score(text: str, concept: ConceptEntry) -> float:
        pref = concept.pref_label.lower()
        text_norm = text.lower()
        if pref == text_norm:
            return 1.0
        if pref in text_norm or text_norm in pref:
            return 0.8
        for alt in concept.alt_labels:
            alt_norm = alt.lower()
            if alt_norm == text_norm:
                return 0.75
            if alt_norm in text_norm or text_norm in alt_norm:
                return 0.6
        return 0.2


__all__ = ["CandidateGenerator"]
