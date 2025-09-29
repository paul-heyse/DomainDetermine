"""Evaluation runner orchestrating execution and telemetry."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping, Sequence

from .metrics import MetricCalculator
from .models import EvalSuite, RunnerConfig


@dataclass
class EvalSuiteRunner:
    """Executes evaluation suites with telemetry and determinism controls."""

    config: RunnerConfig
    metric_calculator: MetricCalculator
    logger: logging.Logger

    def run(self, suite: EvalSuite, predictions: Mapping[str, Sequence[int]], references: Mapping[str, Sequence[int]]) -> Mapping[str, Mapping[str, float]]:
        self.logger.info("eval_suite.start", extra={"suite_id": suite.manifest.suite_id})
        results: dict[str, Mapping[str, float]] = {}
        for metric_id, metric_spec in suite.metrics.items():
            metric_result = self.metric_calculator.compute_metric(
                metric_spec,
                references.get(metric_id, []),
                predictions.get(metric_id, []),
            )
            results[metric_id] = metric_result
            self.logger.info(
                "eval_suite.metric",
                extra={"metric_id": metric_id, "metric_result": metric_result},
            )
        self.logger.info("eval_suite.complete", extra={"suite_id": suite.manifest.suite_id})
        return results


