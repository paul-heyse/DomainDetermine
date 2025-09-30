"""Telemetry helpers for readiness pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Sequence

try:  # Optional OpenTelemetry integration
    from opentelemetry import metrics as otel_metrics
except Exception:  # pragma: no cover - optional dependency
    otel_metrics = None


@dataclass
class MetricPoint:
    """Represents a single metric measurement."""

    name: str
    value: float
    tags: Mapping[str, str] = field(default_factory=dict)


class MetricsEmitter:
    """Telemetry emitter for readiness metrics.

    Emits metrics via OpenTelemetry when available, otherwise buffers measurements.
    """

    def __init__(self, namespace: str = "domain_determine.readiness") -> None:
        self._namespace = namespace
        self._buffer: list[MetricPoint] = []
        self._meter = None
        enable_otel = os.environ.get("READINESS_ENABLE_OTEL", "0") == "1"
        if otel_metrics and enable_otel:
            try:
                self._meter = otel_metrics.get_meter_provider().get_meter(namespace)
            except Exception:  # pragma: no cover - OTEL optional
                self._meter = None
        if self._meter:
            try:
                self._recorders: dict[str, object] = {}
            except Exception:  # pragma: no cover
                self._recorders = {}
        else:
            self._recorders = {}

    def emit(self, name: str, value: float, **tags: str) -> None:
        if self._meter:
            try:
                recorder = self._recorders.get(name)
                if recorder is None:
                    recorder = self._meter.create_histogram(name)
                    self._recorders[name] = recorder
                recorder.record(value, tags)  # type: ignore[attr-defined]
                return
            except Exception:  # pragma: no cover - fall back to buffer
                pass
        point = MetricPoint(name=name, value=value, tags=tags)
        self._buffer.append(point)

    def flush(self) -> Sequence[MetricPoint]:
        data = tuple(self._buffer)
        self._buffer.clear()
        return data
