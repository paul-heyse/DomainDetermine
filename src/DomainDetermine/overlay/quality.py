"""Automated quality gates for overlay candidates."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable, Mapping, Sequence

from DomainDetermine.overlay.exceptions import EvidenceValidationError, QualityGateError
from DomainDetermine.overlay.models import EvidencePack


@dataclass(frozen=True)
class OverlayQualityGateConfig:
    """Configuration values for automated gate checks."""

    duplicate_threshold: float = 0.85
    max_label_length: int = 120
    enforce_language_labels: bool = True


def duplicate_conflict_score(label: str, existing_labels: Iterable[str]) -> float:
    """Return the best similarity score between a label and existing labels."""

    scores = [SequenceMatcher(None, label.lower(), other.lower()).ratio() for other in existing_labels]
    return max(scores, default=0.0)


def ensure_editorial_compliance(
    *,
    label: str,
    config: OverlayQualityGateConfig,
) -> None:
    """Check editorial rules for a proposed label."""

    if not label:
        raise QualityGateError("Overlay label cannot be empty")
    if len(label) > config.max_label_length:
        msg = f"Overlay label '{label}' exceeds maximum length {config.max_label_length}"
        raise QualityGateError(msg)
    first_char = next((character for character in label if character.isalpha()), "")
    if first_char and not first_char.isupper():
        raise QualityGateError("Overlay labels must start with uppercase characters")


def ensure_language_tags(labels: Mapping[str, str], *, config: OverlayQualityGateConfig) -> None:
    if not config.enforce_language_labels:
        return
    for language, value in labels.items():
        if not language:
            raise QualityGateError("Language tag is required for overlay labels")
        if not value:
            raise QualityGateError(f"Preferred label missing text for language '{language}'")


def validate_evidence_pack(evidence_pack: EvidencePack, cited_identifiers: Sequence[str]) -> None:
    """Ensure the evidence pack contains all cited sources."""

    sources = {document.source_id for document in evidence_pack.documents}
    missing = [identifier for identifier in cited_identifiers if identifier not in sources]
    if missing:
        raise EvidenceValidationError(
            f"Cited sources {missing} not present in evidence pack"
        )


def run_quality_gates(
    *,
    preferred_labels: Mapping[str, str],
    new_label: str,
    existing_labels: Iterable[str],
    evidence_pack: EvidencePack,
    cited_identifiers: Sequence[str],
    config: OverlayQualityGateConfig,
) -> None:
    """Run all automated quality checks before human review."""

    ensure_language_tags(preferred_labels, config=config)
    ensure_editorial_compliance(label=new_label, config=config)
    score = duplicate_conflict_score(new_label, existing_labels)
    if score > config.duplicate_threshold:
        raise QualityGateError(
            f"Duplicate/conflict score {score:.2f} exceeds threshold {config.duplicate_threshold:.2f}"
        )
    validate_evidence_pack(evidence_pack, cited_identifiers)


__all__ = [
    "OverlayQualityGateConfig",
    "duplicate_conflict_score",
    "ensure_editorial_compliance",
    "ensure_language_tags",
    "run_quality_gates",
    "validate_evidence_pack",
]
