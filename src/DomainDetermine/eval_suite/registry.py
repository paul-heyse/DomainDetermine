"""Registries for slices and metrics to ensure cross-suite consistency."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional

from .models import MetricSpec, SliceDefinition


@dataclass
class SliceRegistry:
    """Persistent registry of slice definitions."""

    slices: Dict[str, SliceDefinition] = field(default_factory=dict)

    def register(self, slice_def: SliceDefinition) -> None:
        existing = self.slices.get(slice_def.slice_id)
        if existing and existing != slice_def:
            msg = f"Slice '{slice_def.slice_id}' conflicts with existing definition"
            raise ValueError(msg)
        self.slices[slice_def.slice_id] = slice_def

    def get(self, slice_id: str) -> Optional[SliceDefinition]:
        return self.slices.get(slice_id)

    def all(self) -> Mapping[str, SliceDefinition]:
        return dict(self.slices)


@dataclass
class MetricRegistry:
    """Registry of metrics shared across suites."""

    metrics: Dict[str, MetricSpec] = field(default_factory=dict)

    def register(self, spec: MetricSpec) -> None:
        existing = self.metrics.get(spec.metric_id)
        if existing and existing != spec:
            msg = f"Metric '{spec.metric_id}' conflicts with existing definition"
            raise ValueError(msg)
        self.metrics[spec.metric_id] = spec

    def get(self, metric_id: str) -> Optional[MetricSpec]:
        return self.metrics.get(metric_id)

    def all(self) -> Mapping[str, MetricSpec]:
        return dict(self.metrics)


