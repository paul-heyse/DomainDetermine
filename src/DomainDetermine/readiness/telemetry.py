"""Telemetry bootstrap for readiness pipeline."""

from __future__ import annotations

import os
from typing import Mapping

try:  # Optional OpenTelemetry dependency
    from opentelemetry import metrics as otel_metrics
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
except Exception:  # pragma: no cover - OTEL optional
    OTLPMetricExporter = None
    MeterProvider = None
    PeriodicExportingMetricReader = None
    Resource = None
    otel_metrics = None


def _parse_headers(raw: str | None) -> Mapping[str, str]:
    if not raw:
        return {}
    pairs = [segment.strip() for segment in raw.split(",") if segment.strip()]
    result: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def configure_otel(service_name: str = "domain_determine.readiness") -> None:
    """Configure global OTEL meter provider for readiness pipeline if exporters are available."""

    if not (OTLPMetricExporter and MeterProvider and PeriodicExportingMetricReader and Resource and otel_metrics):
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    headers = _parse_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS"))
    try:
        exporter = OTLPMetricExporter(endpoint=endpoint, headers=headers or None)
        reader = PeriodicExportingMetricReader(exporter)
        resource = Resource.create({"service.name": service_name})
        provider = MeterProvider(resource=resource, metric_readers=[reader])
        otel_metrics.set_meter_provider(provider)
    except Exception:  # pragma: no cover - fail gracefully
        return


__all__ = ["configure_otel"]

