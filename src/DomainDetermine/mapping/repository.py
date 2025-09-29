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
        return tuple(self.concepts.values())

    def get(self, concept_id: str) -> ConceptEntry:
        """Retrieve a single concept entry."""

        return self.concepts[concept_id]

