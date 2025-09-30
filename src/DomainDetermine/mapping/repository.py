"""Repository for concept access and candidate preparation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .models import ConceptEntry, MappingContext


@dataclass(slots=True)
class ConceptRepository:
    """In-memory concept lookup supporting faceted restrictions."""

    concepts: dict[str, ConceptEntry]

    def list_candidates(
        self,
        context: MappingContext,
        restriction_ids: Iterable[str] | None = None,
    ) -> Sequence[ConceptEntry]:
        """Return concepts restricted by provided IDs or context facets."""

        if restriction_ids is not None:
            return tuple(
                self.concepts[concept_id]
                for concept_id in restriction_ids
                if concept_id in self.concepts
            )
        if context.allowed_concept_ids:
            return tuple(
                self.concepts[concept_id]
                for concept_id in context.allowed_concept_ids
                if concept_id in self.concepts
            )
        return tuple(
            concept
            for concept in self.concepts.values()
            if self._matches_facets(concept, context)
        )

    def get(self, concept_id: str) -> ConceptEntry:
        """Retrieve a single concept entry."""

        return self.concepts[concept_id]

    @staticmethod
    def _matches_facets(concept: ConceptEntry, context: MappingContext) -> bool:
        for key, value in context.facets.items():
            if key not in concept.facets:
                return False
            if concept.facets[key] != value:
                return False
        return True

