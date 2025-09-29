"""Candidate generation strategies for mapping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .models import Candidate, CandidateSource, ConceptEntry, MappingContext
from .repository import ConceptRepository


@dataclass(slots=True)
class CandidateGenerator:
    """Generates candidate concepts using lexical and semantic heuristics."""

    repository: ConceptRepository

    def generate(
        self,
        query: str,
        context: MappingContext,
        limit: int = 20,
    ) -> Sequence[Candidate]:
        """Generate candidate concepts for the provided query."""

        concepts = self.repository.list_candidates(context)
        lexical_candidates = self._lexical_candidates(query, concepts, limit)
        semantic_candidates = self._semantic_candidates(query, concepts, limit)
        graph_candidates = self._graph_candidates(lexical_candidates, concepts)
        combined = tuple(lexical_candidates + semantic_candidates + graph_candidates)
        unique = self._deduplicate(combined)
        return tuple(sorted(unique, key=lambda candidate: candidate.score, reverse=True)[:limit])

    def _lexical_candidates(
        self,
        query: str,
        concepts: Sequence[ConceptEntry],
        limit: int,
    ) -> list[Candidate]:
        query_tokens = self._tokenize(query)
        candidates: list[Candidate] = []
        for concept in concepts[:limit * 2]:
            label_tokens = self._tokenize(concept.pref_label)
            intersection = query_tokens & label_tokens
            if not intersection:
                continue
            score = len(intersection) / max(len(query_tokens), 1)
            if query.strip().casefold() == concept.pref_label.strip().casefold():
                score = 1.0
            candidates.append(
                Candidate(
                    concept_id=concept.concept_id,
                    label=concept.pref_label,
                    source=CandidateSource.LEXICAL,
                    score=score,
                )
            )
        return candidates

    def _semantic_candidates(
        self,
        query: str,
        concepts: Sequence[ConceptEntry],
        limit: int,
    ) -> list[Candidate]:
        return [
            Candidate(
                concept_id=concept.concept_id,
                label=concept.pref_label,
                source=CandidateSource.SEMANTIC,
                score=0.5,
            )
            for concept in concepts[:limit]
        ]

    def _graph_candidates(
        self,
        lexical_candidates: Iterable[Candidate],
        concepts: Sequence[ConceptEntry],
    ) -> list[Candidate]:
        concept_map = {concept.concept_id: concept for concept in concepts}
        results: list[Candidate] = []
        for candidate in lexical_candidates:
            concept = concept_map.get(candidate.concept_id)
            if not concept:
                continue
            results.extend(
                Candidate(
                    concept_id=broader_id,
                    label=concept_map[broader_id].pref_label,
                    source=CandidateSource.GRAPH,
                    score=candidate.score * 0.8,
                )
                for broader_id in concept.broader
                if broader_id in concept_map
            )
        return results

    @staticmethod
    def _deduplicate(candidates: Sequence[Candidate]) -> list[Candidate]:
        seen: dict[str, Candidate] = {}
        for candidate in candidates:
            existing = seen.get(candidate.concept_id)
            if not existing or candidate.score > existing.score:
                seen[candidate.concept_id] = candidate
        return list(seen.values())

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token for token in text.casefold().split() if token}

