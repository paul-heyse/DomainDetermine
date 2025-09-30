"""Prompt-pack quality yardsticks and evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, MutableMapping

from .metrics import TemplateMetrics


@dataclass(frozen=True)
class AcceptanceYardstick:
    """Defines quality thresholds for a prompt template version."""

    template_id: str
    version: str
    minimums: Mapping[str, float] = field(default_factory=dict)
    maximums: Mapping[str, float] = field(default_factory=dict)

    def evaluate(self, metrics: Mapping[str, float]) -> bool:
        """Return True when the provided metrics satisfy the yardstick."""

        for name, threshold in self.minimums.items():
            if metrics.get(name, float("nan")) < threshold:
                return False
        for name, threshold in self.maximums.items():
            if metrics.get(name, float("inf")) > threshold:
                return False
        return True

    def as_dict(self) -> Mapping[str, Mapping[str, float]]:
        return {
            "template_id": self.template_id,
            "version": self.version,
            "minimums": dict(self.minimums),
            "maximums": dict(self.maximums),
        }


class YardstickRegistry:
    """Registry for acceptance yardsticks keyed by template/version."""

    def __init__(self) -> None:
        self._store: MutableMapping[tuple[str, str], AcceptanceYardstick] = {}

    def register(self, yardstick: AcceptanceYardstick) -> None:
        self._store[(yardstick.template_id, yardstick.version)] = yardstick

    def get(self, template_id: str, version: str) -> AcceptanceYardstick:
        try:
            return self._store[(template_id, version)]
        except KeyError as exc:  # pragma: no cover - simple mapping
            raise KeyError(f"Yardstick not found for {template_id}:{version}") from exc

    def evaluate(self, metrics: TemplateMetrics, *, locale: str = "default") -> bool:
        yardstick = self.get(metrics.template_id, metrics.version)
        locale_metrics = metrics.as_dict().get(locale, {})
        return yardstick.evaluate(locale_metrics)

    def as_dict(self) -> Mapping[str, Mapping[str, Mapping[str, float]]]:
        return {
            f"{template}:{version}": yardstick.as_dict()
            for (template, version), yardstick in self._store.items()
        }


DEFAULT_YARDSTICKS = YardstickRegistry()
DEFAULT_YARDSTICKS.register(
    AcceptanceYardstick(
        template_id="mapping_decision",
        version="1.0.0",
        minimums={
            "grounding_fidelity": 0.9,
            "citation_coverage": 0.95,
            "acceptance_rate": 0.8,
        },
        maximums={
            "hallucination_rate": 0.02,
            "constraint_violations": 0.01,
        },
    )
)


__all__ = [
    "AcceptanceYardstick",
    "YardstickRegistry",
    "DEFAULT_YARDSTICKS",
]
