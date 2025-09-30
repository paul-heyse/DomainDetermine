"""Candidate generator for mapping pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol, Sequence

from rapidfuzz import fuzz

from .models import Candidate, CandidateSource, ConceptEntry, MappingContext
from .repository import ConceptRepository


@dataclass(slots=True)
class SemanticHit:
    """Represents a semantic retrieval result."""

    concept_id: str
    score: float


class SemanticIndex(Protocol):
    """Protocol describing semantic search capability."""

    def search(self, query: str, *, k: int, filters: Mapping[str, str]) -> Sequence[SemanticHit]:  # pragma: no cover - protocol
        ...


@dataclass(slots=True)
class CandidateGenerator:
    """Generates mapping candidates from repository lookups."""

    repository: ConceptRepository
    embedding_index: SemanticIndex | None = None
    max_lexical: int = 10
    max_semantic: int = 15
    max_graph: int = 5

    def generate(self, normalized_text: str, context: MappingContext) -> Sequence[Candidate]:
        lexical = self._lexical_candidates(normalized_text, context)
        semantic = self._semantic_candidates(normalized_text, context)
        graph = self._graph_candidates(lexical, context)
        merged = self._merge_candidates((lexical, semantic, graph))
        return merged

    def _lexical_candidates(self, normalized_text: str, context: MappingContext) -> list[Candidate]:
        entries = self.repository.list_candidates(context)
        results: list[Candidate] = []
        for concept in entries:
            label = concept.pref_label or concept.concept_id
            score = self._lexical_score(normalized_text, label)
            if score <= 0.0:
                continue
            results.append(
                Candidate(
                    concept_id=concept.concept_id,
                    label=label,
                    source=CandidateSource.LEXICAL,
                    score=score,
                    evidence=concept.definition,
                    language=concept.language,
                )
            )
        results.sort(key=lambda candidate: candidate.score, reverse=True)
        return results[: self.max_lexical]

    def _semantic_candidates(self, normalized_text: str, context: MappingContext) -> list[Candidate]:
        if not self.embedding_index:
            return []
        hits = self.embedding_index.search(normalized_text, k=self.max_semantic, filters=context.facets)
        candidates: list[Candidate] = []
        for hit in hits:
            concept = self.repository.get(hit.concept_id)
            candidates.append(
                Candidate(
                    concept_id=concept.concept_id,
                    label=concept.pref_label,
                    source=CandidateSource.SEMANTIC,
                    score=float(hit.score),
                    evidence=concept.definition,
                    language=concept.language,
                )
            )
        return candidates

    def _graph_candidates(self, seeds: Iterable[Candidate], context: MappingContext) -> list[Candidate]:
        seen = {candidate.concept_id for candidate in seeds}
        results: list[Candidate] = []
        for candidate in seeds:
            concept = self.repository.get(candidate.concept_id)
            neighbours = list(concept.broader) + list(concept.narrower)
            for neighbour_id in neighbours:
                if neighbour_id in seen:
                    continue
                seen.add(neighbour_id)
                try:
                    neighbour = self.repository.get(neighbour_id)
                except KeyError:
                    continue
                results.append(
                    Candidate(
                        concept_id=neighbour.concept_id,
                        label=neighbour.pref_label,
                        source=CandidateSource.GRAPH,
                        score=candidate.score * 0.8,
                        evidence=neighbour.definition,
                        language=neighbour.language,
                    )
                )
                if len(results) >= self.max_graph:
                    break
            if len(results) >= self.max_graph:
                break
        return results

    def _merge_candidates(self, groups: Iterable[Sequence[Candidate]]) -> tuple[Candidate, ...]:
        merged: dict[str, Candidate] = {}
        for group in groups:
            for candidate in group:
                existing = merged.get(candidate.concept_id)
                if existing is None or candidate.score > existing.score:
                    merged[candidate.concept_id] = candidate
        ranked = sorted(merged.values(), key=lambda candidate: candidate.score, reverse=True)
        return tuple(ranked)

    @staticmethod
    def _lexical_score(text: str, label: str) -> float:
        return fuzz.token_set_ratio(text, label.lower()) / 100.0


__all__ = ["CandidateGenerator", "SemanticIndex", "SemanticHit"]
