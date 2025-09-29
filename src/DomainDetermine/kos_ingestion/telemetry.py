"""Telemetry helpers for connector instrumentation."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Iterator

from .models import ConnectorMetrics

logger = logging.getLogger(__name__)


@contextmanager
def track_latency(metrics: ConnectorMetrics, metric_name: str) -> Iterator[None]:
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        metrics.observe(metric_name, duration)
        logger.debug("Metric %s recorded duration %.3fs", metric_name, duration)


def record_bytes(metrics: ConnectorMetrics, metric_name: str, size_bytes: int) -> None:
    metrics.observe(metric_name, float(size_bytes))
    logger.debug("Metric %s recorded size %s bytes", metric_name, size_bytes)


def record_status(metrics: ConnectorMetrics, status: str) -> None:
    metrics.incr(f"status.{status}")
    logger.debug("Status %s incremented", status)
