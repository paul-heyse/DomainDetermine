"""Telemetry helpers for the service layer."""

from __future__ import annotations

import os
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

try:  # Optional OpenTelemetry integration
    from opentelemetry import trace
    from opentelemetry.metrics import get_meter
except Exception:  # pragma: no cover - OTEL optional
    trace = None
    get_meter = None


_OTEL_DISABLED = os.getenv("OTEL_SDK_DISABLED") == "1"
_METRICS_DISABLED = os.getenv("OTEL_METRICS_EXPORTER", "").lower() in {"", "none"}
_TRACES_DISABLED = os.getenv("OTEL_TRACES_EXPORTER", "").lower() in {"", "none"}


def _get_tracer(name: str):  # pragma: no cover - thin wrapper
    if trace is None:
        return None
    if _OTEL_DISABLED or _TRACES_DISABLED:
        return None
    return trace.get_tracer(name)


def _get_meter(name: str):  # pragma: no cover - thin wrapper
    if get_meter is None:
        return None
    if _OTEL_DISABLED or _METRICS_DISABLED:
        return None
    return get_meter(name)


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that records request duration and status metrics."""

    def __init__(
        self,
        app,
        *,
        service_name: str = "domain_determine.service",
        slow_query_threshold_ms: float = 0.0,
        on_slow_request: Optional[Callable[[str, float], None]] = None,
    ) -> None:
        super().__init__(app)
        self._tracer = _get_tracer(service_name)
        self._meter = _get_meter(service_name)
        self._slow_query_threshold_ms = slow_query_threshold_ms
        self._slow_request_callback = on_slow_request
        if self._meter:
            try:
                self._request_counter = self._meter.create_counter(
                    "service_requests_total", unit="1", description="Total HTTP requests processed"
                )
                self._request_duration = self._meter.create_histogram(
                    "service_request_duration_ms",
                    unit="ms",
                    description="Request latency in milliseconds",
                )
            except Exception:  # pragma: no cover - meter setup optional
                self._request_counter = None
                self._request_duration = None
        else:  # pragma: no cover - meter optional
            self._request_counter = None
            self._request_duration = None

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        span = None
        if self._tracer:
            span = self._tracer.start_span(
                "http.request",
                attributes={
                    "http.method": request.method,
                    "http.route": request.url.path,
                },
            )
        response: Optional[Response] = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            status_code = 0
            try:
                status_code = response.status_code  # type: ignore[attr-defined]
            except Exception:
                status_code = 500
            if span:
                span.set_attribute("http.status_code", status_code)
                span.set_attribute("http.duration_ms", duration_ms)
                span.end()
            if self._request_counter:
                try:
                    self._request_counter.add(1, attributes={
                        "http.method": request.method,
                        "http.route": request.url.path,
                        "http.status_code": str(status_code),
                    })
                except Exception:  # pragma: no cover - metrics optional
                    pass
            if self._request_duration:
                try:
                    self._request_duration.record(
                        duration_ms,
                        attributes={
                            "http.method": request.method,
                            "http.route": request.url.path,
                        },
                    )
                except Exception:  # pragma: no cover
                    pass
            if (
                self._slow_query_threshold_ms
                and duration_ms > self._slow_query_threshold_ms
                and self._slow_request_callback
            ):
                try:
                    self._slow_request_callback(request.url.path, duration_ms)
                except Exception:  # pragma: no cover - defensive callback guard
                    pass


@dataclass
class SlowRequestTracker:
    """Ring buffer that retains the most recent slow request warnings."""

    max_entries: int = 50
    _entries: Deque[str] = field(init=False)

    def __post_init__(self) -> None:
        self._entries = deque(maxlen=self.max_entries)

    def record(self, path: str, duration_ms: float) -> None:
        message = f"{path} took {duration_ms:.1f}ms"
        self._entries.append(message)

    def snapshot(self) -> list[str]:
        return list(self._entries)


@contextmanager
def job_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Context manager that records a span for job execution if OTEL is available."""

    tracer = _get_tracer("domain_determine.service.jobs")
    if tracer is None:
        yield None
        return
    attrs = attributes or {}
    with tracer.start_as_current_span(name, attributes=attrs) as span:
        yield span


def record_job_metric(name: str, value: float, attributes: Optional[Dict[str, Any]] = None) -> None:
    meter = _get_meter("domain_determine.service.jobs")
    if meter is None:  # pragma: no cover - optional
        return
    try:
        histogram = meter.create_histogram(name, unit="ms")
        histogram.record(value, attributes=attributes or {})
    except Exception:  # pragma: no cover - defensive
        return


__all__ = ["TelemetryMiddleware", "job_span", "record_job_metric"]
