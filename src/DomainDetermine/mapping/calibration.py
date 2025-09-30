"""Calibration harness for the mapping pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from .models import MappingBatchResult, MappingContext, MappingItem
from .pipeline import MappingPipeline


@dataclass(slots=True)
class CalibrationExample:
    """Represents a single gold example for calibration."""

    text: str
    expected_concept_id: str
    context: MappingContext = field(default_factory=MappingContext)


@dataclass(slots=True)
class CalibrationResult:
    """Aggregated metrics from a calibration run."""

    total: int
    resolved: int
    correct: int
    metrics: Mapping[str, float]
    precision_at_1: float
    recall_at_k: float

    @property
    def accuracy(self) -> float:
        return self.metrics.get("accuracy", 0.0)

    @property
    def resolution_rate(self) -> float:
        return self.metrics.get("resolution_rate", 0.0)


class MappingCalibrationSuite:
    """Runs a mapping pipeline against a gold set and reports metrics."""

    def __init__(self, pipeline: MappingPipeline) -> None:
        self._pipeline = pipeline

    def run(self, examples: Iterable[CalibrationExample]) -> CalibrationResult:
        example_list = list(examples)
        items = [MappingItem(example.text, example.context) for example in example_list]
        batch = self._pipeline.run(items)
        resolved_map = self._build_resolution_map(batch)
        correct = 0
        for example in example_list:
            record = resolved_map.get(example.text)
            if record and record.concept_id == example.expected_concept_id:
                correct += 1
        total = len(example_list)
        resolved = len(resolved_map)
        precision_at_1 = correct / resolved if resolved else 0.0
        recall_at_k = correct / total if total else 0.0
        metrics = dict(batch.metrics)
        metrics["accuracy"] = recall_at_k
        metrics.setdefault("resolution_rate", resolved / total if total else 0.0)
        metrics["precision_at_1"] = precision_at_1
        metrics["recall_at_k"] = recall_at_k
        return CalibrationResult(
            total=total,
            resolved=resolved,
            correct=correct,
            metrics=metrics,
            precision_at_1=precision_at_1,
            recall_at_k=recall_at_k,
        )

    @staticmethod
    def _build_resolution_map(batch: MappingBatchResult):
        return {record.mapping_item.source_text: record for record in batch.records}


