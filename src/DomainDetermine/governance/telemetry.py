"""Governance observability instrumentation."""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import mean
from typing import Deque, Iterable, Mapping, Optional

try:  # Optional OpenTelemetry integration
    from opentelemetry import metrics as otel_metrics
    from opentelemetry import trace
except Exception:  # pragma: no cover
    otel_metrics = None
    trace = None

from DomainDetermine.governance.event_log import GovernanceEventType
from DomainDetermine.governance.models import ArtifactRef


@dataclass
class GovernanceTelemetry:
    """Captures governance SLIs/SLOs and aggregates metrics."""

    _publish_lead_times: Deque[float] = field(default_factory=lambda: deque(maxlen=200))
    _audit_failures: int = 0
    _rollbacks: int = 0
    _latencies_ms: Deque[float] = field(default_factory=lambda: deque(maxlen=500))
    _events: Deque[Mapping[str, object]] = field(default_factory=lambda: deque(maxlen=1000))
    _readiness_summaries: Deque[Mapping[str, object]] = field(default_factory=lambda: deque(maxlen=50))
    _registry_notifications: Deque[Mapping[str, object]] = field(
        default_factory=lambda: deque(maxlen=200)
    )
    _meter = None
    _tracer = None
    _hist_publish_lead: Optional[object] = None
    _counter_audit_failures: Optional[object] = None
    _counter_rollbacks: Optional[object] = None
    _hist_latency: Optional[object] = None

    def __post_init__(self) -> None:
        enable_otel = os.environ.get("GOVERNANCE_ENABLE_OTEL", "0") == "1"
        if otel_metrics and enable_otel:
            try:
                self._meter = otel_metrics.get_meter_provider().get_meter("domain_determine.governance")
                self._hist_publish_lead = self._meter.create_histogram(
                    "governance.publish_lead_time_seconds", unit="s"
                )
                self._counter_audit_failures = self._meter.create_counter(
                    "governance.audit_failures_total"
                )
                self._counter_rollbacks = self._meter.create_counter(
                    "governance.rollbacks_total"
                )
                self._hist_latency = self._meter.create_histogram(
                    "governance.registry_latency_ms", unit="ms"
                )
            except Exception:  # pragma: no cover
                self._meter = None
        if trace and enable_otel:
            self._tracer = trace.get_tracer("domain_determine.governance")

    def record_publish(self, *, proposed_at: datetime, published_at: datetime) -> None:
        lead_time = (published_at - proposed_at).total_seconds()
        self._publish_lead_times.append(lead_time)
        if self._hist_publish_lead:
            try:
                self._hist_publish_lead.record(lead_time)
            except Exception:  # pragma: no cover
                pass
        self._events.append(
            {
                "type": "publish",
                "lead_time_seconds": lead_time,
                "published_at": published_at.isoformat(),
            }
        )
        if self._tracer:
            span = self._tracer.start_span(
                "governance.publish",
                attributes={
                    "governance.lead_time_seconds": lead_time,
                    "governance.event": "publish",
                },
            )
            span.end()

    def record_audit_failure(self, *, artifact_id: str, reason: str) -> None:
        self._audit_failures += 1
        if self._counter_audit_failures:
            try:
                self._counter_audit_failures.add(1, attributes={"artifact_id": artifact_id})
            except Exception:  # pragma: no cover
                pass
        self._events.append(
            {
                "type": "audit_failure",
                "artifact_id": artifact_id,
                "reason": reason,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if self._tracer:
            span = self._tracer.start_span(
                "governance.audit_failure",
                attributes={"artifact_id": artifact_id, "reason": reason},
            )
            span.end()

    def record_rollback(self, *, artifact_id: str) -> None:
        self._rollbacks += 1
        if self._counter_rollbacks:
            try:
                self._counter_rollbacks.add(1, attributes={"artifact_id": artifact_id})
            except Exception:  # pragma: no cover
                pass
        self._events.append(
            {
                "type": "rollback",
                "artifact_id": artifact_id,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if self._tracer:
            span = self._tracer.start_span(
                "governance.rollback",
                attributes={"artifact_id": artifact_id},
            )
            span.end()

    def record_registry_latency(self, latency_ms: float) -> None:
        self._latencies_ms.append(latency_ms)
        if self._hist_latency:
            try:
                self._hist_latency.record(latency_ms)
            except Exception:  # pragma: no cover
                pass
        self._events.append(
            {
                "type": "registry_latency",
                "latency_ms": latency_ms,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def record_readiness_summary(
        self,
        *,
        generated_at: datetime,
        overall_passed: bool,
        failures: Iterable[str],
        coverage: Mapping[str, float],
    ) -> None:
        summary = {
            "type": "readiness_summary",
            "generated_at": generated_at.isoformat(),
            "overall_passed": overall_passed,
            "failures": list(failures),
            "coverage": dict(coverage),
        }
        self._events.append(summary)
        self._readiness_summaries.append(summary)

    def record_registry_notification(
        self,
        *,
        event_type: GovernanceEventType,
        artifact: ArtifactRef,
        actor: str,
        payload: Mapping[str, object],
    ) -> None:
        """Capture registry events for readiness dashboards."""

        event = {
            "type": "registry_event",
            "event_type": event_type.value,
            "artifact_id": artifact.artifact_id,
            "artifact_version": artifact.version,
            "artifact_hash": artifact.hash,
            "actor": actor,
            "payload": dict(payload),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        self._events.append(event)
        self._registry_notifications.append(event)

    def record_rehearsal(
        self,
        *,
        rehearsal_time: datetime,
        max_age_days: int,
        stale: bool,
        release_id: str | None = None,
    ) -> None:
        """Record a rollback rehearsal check with telemetry."""

        event = {
            "type": "rollback_rehearsal",
            "rehearsed_at": rehearsal_time.isoformat(),
            "stale": stale,
            "max_age_days": max_age_days,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        if release_id:
            event["release_id"] = release_id
        self._events.append(event)
        if self._tracer:
            span = self._tracer.start_span(
                "governance.rollback_rehearsal",
                attributes={
                    "rollback.rehearsed_at": rehearsal_time.isoformat(),
                    "rollback.stale": stale,
                    "rollback.max_age_days": max_age_days,
                    "release.id": release_id or "",
                },
            )
            span.end()

    def metrics_snapshot(self) -> Mapping[str, object]:
        lead_time_avg = mean(self._publish_lead_times) if self._publish_lead_times else 0.0
        latency_p95 = self._percentile(self._latencies_ms, percentile=95)
        return {
            "publish_lead_time_avg": lead_time_avg,
            "publish_samples": len(self._publish_lead_times),
            "audit_failure_count": self._audit_failures,
            "rollback_count": self._rollbacks,
            "registry_latency_p95_ms": latency_p95,
            "readiness_last": self._readiness_summaries[-1] if self._readiness_summaries else None,
        }

    def recent_events(self, limit: int = 50) -> Iterable[Mapping[str, object]]:
        slice_start = max(len(self._events) - limit, 0)
        return list(list(self._events)[slice_start:])

    def latest_readiness(self) -> Optional[Mapping[str, object]]:
        if not self._readiness_summaries:
            return None
        return self._readiness_summaries[-1]

    def readiness_notifications(self, limit: int = 50) -> Iterable[Mapping[str, object]]:
        if limit <= 0:
            return []
        notifications = list(self._registry_notifications)
        if len(notifications) <= limit:
            return notifications
        return notifications[-limit:]

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
