"""Automated validators for prompt-pack quality metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

DEFAULT_BANNED_TOKENS = ("<hallucination>", "[hallucination]", "UNKNOWN", "N/A")


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of prompt quality validation."""

    template_id: str
    version: str
    locale: str
    metrics: Mapping[str, float]
    issues: Sequence[str] = field(default_factory=tuple)

    def passed(self) -> bool:
        return not self.issues


class PromptQualityValidator:
    """Evaluate responses for grounding, hallucination, and constraint adherence."""

    def __init__(
        self,
        *,
        banned_tokens: Sequence[str] | None = None,
        minimum_confidence: float = 0.85,
    ) -> None:
        self._banned_tokens = tuple(banned_tokens or DEFAULT_BANNED_TOKENS)
        self._minimum_confidence = minimum_confidence

    def evaluate(
        self,
        *,
        template_id: str,
        version: str,
        locale: str,
        response: Mapping[str, object],
        context: Mapping[str, object] | None = None,
    ) -> ValidationResult:
        issues: list[str] = []
        metrics: dict[str, float] = {}

        evidence = response.get("evidence", [])
        context_text = " ".join(str(value) for value in (context or {}).values())
        if isinstance(evidence, Sequence) and evidence:
            matches = sum(1 for item in evidence if isinstance(item, str) and item in context_text)
            fidelity = matches / len(evidence)
            metrics["grounding_fidelity"] = round(fidelity, 3)
            metrics["citation_coverage"] = round(len(evidence) / max(len(evidence), 1), 3)
        else:
            metrics["grounding_fidelity"] = 0.0
            metrics["citation_coverage"] = 0.0
            issues.append("missing_evidence")

        response_text = " ".join(str(value) for value in response.values())
        hallucinations = [token for token in self._banned_tokens if token.lower() in response_text.lower()]
        metrics["hallucination_rate"] = 1.0 if hallucinations else 0.0
        if hallucinations:
            issues.append("hallucination_detected")

        confidence = float(response.get("confidence", 0.0))
        metrics["acceptance_rate"] = 1.0 if confidence >= self._minimum_confidence else 0.0
        if "concept_id" not in response:
            issues.append("missing_concept_id")
            metrics["constraint_violations"] = metrics.get("constraint_violations", 0.0) + 1.0
        if "confidence" not in response:
            issues.append("missing_confidence")
            metrics["constraint_violations"] = metrics.get("constraint_violations", 0.0) + 1.0
        metrics.setdefault("constraint_violations", 0.0)

        return ValidationResult(
            template_id=template_id,
            version=version,
            locale=locale,
            metrics=metrics,
            issues=tuple(issues),
        )


__all__ = [
    "PromptQualityValidator",
    "ValidationResult",
]
