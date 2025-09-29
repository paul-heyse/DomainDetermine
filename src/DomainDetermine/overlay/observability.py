"""Observability, risk controls, and internationalization utilities for Module 4."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
from statistics import mean
from typing import Mapping, MutableMapping, Optional, Sequence

from DomainDetermine.overlay.exceptions import PolicyViolationError
from DomainDetermine.overlay.models import EvidencePack, OverlayNode
from DomainDetermine.overlay.quality import duplicate_conflict_score


@dataclass(frozen=True)
class PromptLogEntry:
    """Structured log of an LLM invocation."""

    overlay_id: str
    prompt_hash: str
    evidence_hash: str
    response_hash: str
    model: str
    latency_ms: float
    tenant: str


@dataclass(frozen=True)
class DecisionLogEntry:
    """Record of reviewer or pilot decisions for SLA tracking."""

    overlay_id: str
    reviewer_id: str
    decision: str
    latency_ms: float
    rationale: Optional[str]


@dataclass(frozen=True)
class OverlayMetrics:
    """Aggregated KPIs for dashboards."""

    acceptance_rate: float
    coverage_gain: float
    average_pilot_iaa: float
    rejection_reasons: Mapping[str, int]
    reviewer_sla_breaches: int


class OverlayLogger:
    """Captures prompt and decision events for observability dashboards."""

    def __init__(self) -> None:
        self._prompt_logs: list[PromptLogEntry] = []
        self._decision_logs: list[DecisionLogEntry] = []
        self._coverage_gains: MutableMapping[str, float] = {}
        self._pilot_iaa: list[float] = []

    def log_prompt(
        self,
        *,
        overlay_id: str,
        prompt_hash: str,
        evidence_hash: str,
        response_payload: str,
        model: str,
        latency_ms: float,
        tenant: str,
    ) -> None:
        response_hash = sha256(response_payload.encode()).hexdigest()
        self._prompt_logs.append(
            PromptLogEntry(
                overlay_id=overlay_id,
                prompt_hash=prompt_hash,
                evidence_hash=evidence_hash,
                response_hash=response_hash,
                model=model,
                latency_ms=latency_ms,
                tenant=tenant,
            )
        )

    def log_decision(
        self,
        *,
        overlay_id: str,
        reviewer_id: str,
        decision: str,
        latency_ms: float,
        rationale: Optional[str],
    ) -> None:
        self._decision_logs.append(
            DecisionLogEntry(
                overlay_id=overlay_id,
                reviewer_id=reviewer_id,
                decision=decision,
                latency_ms=latency_ms,
                rationale=rationale,
            )
        )

    def record_coverage_gain(self, branch: str, gain: float) -> None:
        self._coverage_gains[branch] = self._coverage_gains.get(branch, 0.0) + gain

    def record_pilot(self, iaa: float) -> None:
        self._pilot_iaa.append(iaa)

    def metrics(self) -> OverlayMetrics:
        accepted = sum(1 for decision in self._decision_logs if decision.decision == "accept")
        total = len(self._decision_logs)
        acceptance_rate = accepted / total if total else 0.0
        coverage_gain = sum(self._coverage_gains.values())
        average_pilot_iaa = mean(self._pilot_iaa) if self._pilot_iaa else 0.0
        reasons = Counter(decision.decision for decision in self._decision_logs if decision.decision != "accept")
        sla_breaches = sum(1 for decision in self._decision_logs if decision.latency_ms > 86_400_000)
        return OverlayMetrics(
            acceptance_rate=acceptance_rate,
            coverage_gain=coverage_gain,
            average_pilot_iaa=average_pilot_iaa,
            rejection_reasons=dict(reasons),
            reviewer_sla_breaches=sla_breaches,
        )

    @property
    def prompt_logs(self) -> Sequence[PromptLogEntry]:
        return tuple(self._prompt_logs)

    @property
    def decision_logs(self) -> Sequence[DecisionLogEntry]:
        return tuple(self._decision_logs)


@dataclass(frozen=True)
class RiskControlConfig:
    """Configuration for risk control enforcement."""

    forbidden_terms: Sequence[str] = field(default_factory=tuple)
    protected_categories: Sequence[str] = field(default_factory=tuple)
    license_tags: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskSignal:
    """Provides contextual information about detected risks."""

    risk_type: str
    detail: str


class RiskControlEngine:
    """Applies hallucination, bias, and licensing checks."""

    def __init__(self, config: RiskControlConfig) -> None:
        self._config = config

    def evaluate(
        self,
        *,
        candidate_label: str,
        justification: str,
        evidence_pack: EvidencePack,
    ) -> Sequence[RiskSignal]:
        signals: list[RiskSignal] = []
        lower_label = candidate_label.lower()
        for term in self._config.forbidden_terms:
            if term.lower() in lower_label:
                signals.append(RiskSignal("policy", f"Forbidden term '{term}' present"))
        for category in self._config.protected_categories:
            if category.lower() in justification.lower():
                signals.append(RiskSignal("bias", f"Protected category '{category}' referenced"))
        license_tag = self._config.license_tags.get(candidate_label)
        if license_tag == "restricted" and evidence_pack.documents:
            signals.append(RiskSignal("license", "Restricted content must be masked"))
        missing_quotes = [
            document
            for document in evidence_pack.documents
            if document.text.strip() == ""
        ]
        if missing_quotes:
            signals.append(RiskSignal("hallucination", "Evidence pack contains empty quote"))
        return tuple(signals)

    def enforce(self, signals: Sequence[RiskSignal]) -> None:
        blocking = [signal for signal in signals if signal.risk_type in {"policy", "license"}]
        if blocking:
            details = ", ".join(signal.detail for signal in blocking)
            raise PolicyViolationError(details)


class InternationalizationValidator:
    """Enforces language tags, jurisdiction variants, and cross-lingual duplication checks."""

    def __init__(self, *, duplicate_threshold: float = 0.9) -> None:
        self._duplicate_threshold = duplicate_threshold

    def validate_labels(self, labels: Mapping[str, Mapping[str, Sequence[str]]]) -> None:
        for overlay_id, language_map in labels.items():
            for language, entries in language_map.items():
                if not language:
                    raise PolicyViolationError(f"Overlay node '{overlay_id}' missing language tag")
                for entry in entries:
                    if not entry:
                        raise PolicyViolationError(f"Overlay node '{overlay_id}' missing label text for {language}")

    def detect_cross_lingual_duplicates(
        self,
        overlays: Sequence[OverlayNode],
    ) -> Sequence[tuple[str, str, float]]:
        collisions: list[tuple[str, str, float]] = []
        for idx, primary in enumerate(overlays):
            primary_labels = {
                label
                for label in primary.preferred_labels.values()
            }
            for secondary in overlays[idx + 1 :]:
                secondary_labels = {label for label in secondary.preferred_labels.values()}
                score = max(
                    duplicate_conflict_score(label, secondary_labels) for label in primary_labels
                ) if primary_labels and secondary_labels else 0.0
                if score >= self._duplicate_threshold:
                    collisions.append((primary.overlay_id, secondary.overlay_id, score))
        return tuple(collisions)


__all__ = [
    "DecisionLogEntry",
    "InternationalizationValidator",
    "OverlayLogger",
    "OverlayMetrics",
    "PromptLogEntry",
    "RiskControlConfig",
    "RiskControlEngine",
    "RiskSignal",
]
