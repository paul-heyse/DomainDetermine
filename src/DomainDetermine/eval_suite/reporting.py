"""Reporting helpers for Module 6."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass
class Scorecard:
    """Structured scorecard containing slice metrics."""

    suite_id: str
    suite_version: str
    slice_metrics: Mapping[str, Mapping[str, float]]
    safety_findings: Sequence[str]
    fairness_notes: Sequence[str]


@dataclass
class ReportGenerator:
    """Creates human-readable report artifacts."""

    def build_scorecard(self, suite_id: str, suite_version: str, metrics: Mapping[str, Mapping[str, float]]) -> Scorecard:
        safety = []
        fairness = []
        for metric_id, payload in metrics.items():
            if metric_id.startswith("safety_") and payload.get("value", 0.0) > 0.0:
                safety.append(f"Safety alert for {metric_id}")
            if metric_id.startswith("fairness_"):
                fairness.append(f"Fairness note for {metric_id}")
        return Scorecard(
            suite_id=suite_id,
            suite_version=suite_version,
            slice_metrics=metrics,
            safety_findings=tuple(safety),
            fairness_notes=tuple(fairness),
        )


