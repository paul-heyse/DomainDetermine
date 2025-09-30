"""Policy guardrails for mapping decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(slots=True)
class MappingGuardrailConfig:
    """Configuration thresholds for mapping guardrails."""

    min_lexical_overlap: float = 0.2
    max_edit_distance: int = 3
    allow_language_mismatch: bool = False


class MappingPolicyGuardrails:
    """Evaluates guardrails for mapping decisions."""

    def __init__(self, config: MappingGuardrailConfig | None = None) -> None:
        self._config = config or MappingGuardrailConfig()

    def check_lexical_overlap(self, overlap: float) -> bool:
        return overlap >= self._config.min_lexical_overlap

    def check_edit_distance(self, distance: int) -> bool:
        return distance <= self._config.max_edit_distance

    def check_language(self, input_lang: str, concept_langs: Sequence[str]) -> bool:
        if self._config.allow_language_mismatch:
            return True
        normalized = input_lang or "und"
        if normalized == "und":
            return True
        return normalized in concept_langs
