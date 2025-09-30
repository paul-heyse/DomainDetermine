"""Telemetry collection for the Triton-hosted LLM stack."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, MutableMapping, Optional

try:  # Optional OpenTelemetry dependency
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.metrics import Meter
except Exception:  # pragma: no cover - OTEL optional
    otel_metrics = None
    Meter = None


@dataclass(slots=True)
class LLMInvocationMetrics:
    """Aggregated metrics derived from provider logs and return_perf_metrics."""

    total_requests: int = 0
    latency_ms_total: float = 0.0
    queue_delay_us_total: float = 0.0
    tokens_in_total: float = 0.0
    tokens_out_total: float = 0.0
    kv_reuse_hits: int = 0
    kv_reuse_misses: int = 0
    speculative_attempts: int = 0
    speculative_accepts: int = 0

    def record(self, payload: Mapping[str, Any]) -> None:
        """Update aggregates with a single invocation payload."""

        self.total_requests += 1
        latency = payload.get("duration_ms")
        if isinstance(latency, (int, float)):
            self.latency_ms_total += float(latency)
        queue_delay = payload.get("queue_delay_us")
        if isinstance(queue_delay, (int, float)):
            self.queue_delay_us_total += float(queue_delay)
        tokens_in = payload.get("tokens_in")
        if isinstance(tokens_in, (int, float)):
            self.tokens_in_total += float(tokens_in)
        tokens_out = payload.get("tokens_out")
        if isinstance(tokens_out, (int, float)):
            self.tokens_out_total += float(tokens_out)
        kv_reuse = payload.get("kv_cache_reuse")
        if isinstance(kv_reuse, Mapping):
            hits = kv_reuse.get("hits")
            misses = kv_reuse.get("misses")
            if isinstance(hits, (int, float)):
                self.kv_reuse_hits += int(hits)
            if isinstance(misses, (int, float)):
                self.kv_reuse_misses += int(misses)
        spec = payload.get("speculative")
        if isinstance(spec, Mapping):
            attempts = spec.get("attempts")
            accepts = spec.get("accepts")
            if isinstance(attempts, (int, float)):
                self.speculative_attempts += int(attempts)
            if isinstance(accepts, (int, float)):
                self.speculative_accepts += int(accepts)

    def snapshot(self) -> Mapping[str, Any]:
        """Return averages and totals for dashboards."""

        if self.total_requests == 0:
            return {
                "requests": 0,
                "latency_avg_ms": 0.0,
                "queue_delay_avg_us": 0.0,
                "tokens_in_avg": 0.0,
                "tokens_out_avg": 0.0,
                "kv_reuse_ratio": 0.0,
                "speculative_accept_ratio": 0.0,
            }
        kv_total = self.kv_reuse_hits + self.kv_reuse_misses
        accept_ratio = (
            float(self.speculative_accepts) / self.speculative_attempts
            if self.speculative_attempts
            else 0.0
        )
        kv_ratio = float(self.kv_reuse_hits) / kv_total if kv_total else 0.0
        return {
            "requests": self.total_requests,
            "latency_avg_ms": self.latency_ms_total / self.total_requests,
            "queue_delay_avg_us": self.queue_delay_us_total / self.total_requests,
            "tokens_in_avg": self.tokens_in_total / self.total_requests,
            "tokens_out_avg": self.tokens_out_total / self.total_requests,
            "kv_reuse_ratio": kv_ratio,
            "speculative_accept_ratio": accept_ratio,
        }


@dataclass(slots=True)
class LLMObservability:
    """Collects provider logs, perf metrics, and governance events."""

    metrics: LLMInvocationMetrics = field(default_factory=LLMInvocationMetrics)
    _events: list[MutableMapping[str, Any]] = field(default_factory=list)
    _logger: logging.Logger = field(default_factory=lambda: logging.getLogger("DomainDetermine.llm.observability"))
    meter_name: str = "domain_determine.llm"
    _meter: Optional[Meter] = field(init=False, default=None)
    _histograms: MutableMapping[str, Any] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        if otel_metrics:
            try:
                provider = otel_metrics.get_meter_provider()
                if provider:
                    self._meter = provider.get_meter(self.meter_name)
                    self._histograms = {
                        "latency_ms": self._meter.create_histogram("llm.latency_ms"),
                        "queue_delay_us": self._meter.create_histogram("llm.queue_delay_us"),
                        "tokens_in": self._meter.create_histogram("llm.tokens_in"),
                        "tokens_out": self._meter.create_histogram("llm.tokens_out"),
                        "kv_reuse_ratio": self._meter.create_histogram("llm.kv_reuse_ratio"),
                        "speculative_accept_ratio": self._meter.create_histogram("llm.speculative_accept_ratio"),
                        "cost_usd": self._meter.create_histogram("llm.cost_usd"),
                        "error_rate": self._meter.create_histogram("llm.error_rate"),
                    }
            except Exception:  # pragma: no cover - OTEL optional
                self._meter = None
                self._histograms = {}

    def record_request(self, payload: Mapping[str, Any]) -> None:
        """Capture a structured provider log entry."""

        enriched = dict(payload)
        enriched.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
        self._events.append(enriched)
        self.metrics.record(enriched)
        self._logger.debug("llm.observability.event", extra={"llm": enriched})
        self._emit_metrics(enriched)

    def recent_events(self, limit: int = 50) -> Iterable[Mapping[str, Any]]:
        return self._events[-limit:]

    def metrics_snapshot(self) -> Mapping[str, Any]:
        snapshot = self.metrics.snapshot()
        snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()
        return snapshot

    def _emit_metrics(self, payload: Mapping[str, Any]) -> None:
        if not self._histograms:
            return
        tags = {
            "model": str(payload.get("model", "unknown")),
            "schema_id": str(payload.get("schema_id", "unknown")),
            "operation": str(payload.get("operation", "unknown")),
            "engine_hash": str(payload.get("engine_hash", "unknown")),
        }
        duration = payload.get("duration_ms")
        if isinstance(duration, (int, float)):
            self._histograms["latency_ms"].record(float(duration), tags)
        queue_delay = payload.get("queue_delay_us")
        if isinstance(queue_delay, (int, float)):
            self._histograms["queue_delay_us"].record(float(queue_delay), tags)
        tokens_in = payload.get("tokens_in")
        if isinstance(tokens_in, (int, float)):
            self._histograms["tokens_in"].record(float(tokens_in), tags)
        tokens_out = payload.get("tokens_out")
        if isinstance(tokens_out, (int, float)):
            self._histograms["tokens_out"].record(float(tokens_out), tags)
        kv_metrics = payload.get("kv_cache_reuse")
        if isinstance(kv_metrics, Mapping):
            hits = kv_metrics.get("hits")
            misses = kv_metrics.get("misses")
            total = 0.0
            if isinstance(hits, (int, float)):
                total += float(hits)
            if isinstance(misses, (int, float)):
                total += float(misses)
            if total:
                ratio = float(hits) / total if isinstance(hits, (int, float)) else 0.0
                self._histograms["kv_reuse_ratio"].record(ratio, tags)
        speculative = payload.get("speculative")
        if isinstance(speculative, Mapping):
            attempts = speculative.get("attempts")
            accepts = speculative.get("accepts")
            if isinstance(attempts, (int, float)) and attempts:
                ratio = float(accepts) / float(attempts) if isinstance(accepts, (int, float)) else 0.0
                self._histograms["speculative_accept_ratio"].record(ratio, tags)
        cost = payload.get("cost_usd")
        if isinstance(cost, (int, float)):
            self._histograms["cost_usd"].record(float(cost), tags)
        error = payload.get("error")
        if isinstance(error, (int, float)):
            self._histograms["error_rate"].record(float(error), tags)


__all__ = ["LLMObservability", "LLMInvocationMetrics"]
