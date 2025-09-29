"""Metric calculation and statistical treatment utilities."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from statistics import mean
from typing import Mapping, Sequence

from .models import MetricSpec


@dataclass
class MetricCalculator:
    """Compute metrics and confidence intervals for slices and suites."""

    bootstrap_samples: int = 200
    random_seed: int = 42

    def compute_metric(self, spec: MetricSpec, labels: Sequence[int], predictions: Sequence[int]) -> Mapping[str, float]:
        if len(labels) != len(predictions):
            raise ValueError("Labels and predictions length mismatch")
        if not labels:
            return {"metric_id": spec.metric_id, "value": 0.0, "ci_low": 0.0, "ci_high": 0.0}
        matches = [1.0 if label == prediction else 0.0 for label, prediction in zip(labels, predictions)]
        accuracy = float(mean(matches))
        ci_low, ci_high = self._bootstrap_interval(matches)
        return {
            "metric_id": spec.metric_id,
            "value": accuracy,
            "ci_low": ci_low,
            "ci_high": ci_high,
        }

    def _bootstrap_interval(self, samples: Sequence[float]) -> tuple[float, float]:
        rng = Random(self.random_seed)
        resampled_means = []
        for _ in range(self.bootstrap_samples):
            resample = [rng.choice(samples) for _ in samples]
            resampled_means.append(float(mean(resample)))
        resampled_means.sort()
        lower_index = max(int(0.025 * len(resampled_means)) - 1, 0)
        upper_index = min(int(0.975 * len(resampled_means)), len(resampled_means) - 1)
        return resampled_means[lower_index], resampled_means[upper_index]


