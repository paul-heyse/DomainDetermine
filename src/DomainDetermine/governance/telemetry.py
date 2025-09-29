"""Governance observability instrumentation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import mean
from typing import Deque, Iterable, Mapping


@dataclass
class GovernanceTelemetry:
    """Captures governance SLIs/SLOs and aggregates metrics."""

    _publish_lead_times: Deque[float] = field(default_factory=lambda: deque(maxlen=200))
    _audit_failures: int = 0
    _rollbacks: int = 0
    _latencies_ms: Deque[float] = field(default_factory=lambda: deque(maxlen=500))
    _events: Deque[Mapping[str, object]] = field(default_factory=lambda: deque(maxlen=1000))

    def record_publish(self, *, proposed_at: datetime, published_at: datetime) -> None:
        lead_time = (published_at - proposed_at).total_seconds()
        self._publish_lead_times.append(lead_time)
        self._events.append(
            {
                "type": "publish",
                "lead_time_seconds": lead_time,
                "published_at": published_at.isoformat(),
            }
        )

    def record_audit_failure(self, *, artifact_id: str, reason: str) -> None:
        self._audit_failures += 1
        self._events.append(
            {
                "type": "audit_failure",
                "artifact_id": artifact_id,
                "reason": reason,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def record_rollback(self, *, artifact_id: str) -> None:
        self._rollbacks += 1
        self._events.append(
            {
                "type": "rollback",
                "artifact_id": artifact_id,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def record_registry_latency(self, latency_ms: float) -> None:
        self._latencies_ms.append(latency_ms)
        self._events.append(
            {
                "type": "registry_latency",
                "latency_ms": latency_ms,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def metrics_snapshot(self) -> Mapping[str, object]:
        lead_time_avg = mean(self._publish_lead_times) if self._publish_lead_times else 0.0
        latency_p95 = self._percentile(self._latencies_ms, percentile=95)
        return {
            "publish_lead_time_avg": lead_time_avg,
            "publish_samples": len(self._publish_lead_times),
            "audit_failure_count": self._audit_failures,
            "rollback_count": self._rollbacks,
            "registry_latency_p95_ms": latency_p95,
        }

    def recent_events(self, limit: int = 50) -> Iterable[Mapping[str, object]]:
        slice_start = max(len(self._events) - limit, 0)
        return list(list(self._events)[slice_start:])

    @staticmethod
    def _percentile(values: Iterable[float], *, percentile: float) -> float:
        data = sorted(values)
        if not data:
            return 0.0
        k = (len(data) - 1) * percentile / 100
        f = int(k)
        c = min(f + 1, len(data) - 1)
        if f == c:
            return data[int(k)]
        return data[f] + (data[c] - data[f]) * (k - f)


__all__ = ["GovernanceTelemetry"]
