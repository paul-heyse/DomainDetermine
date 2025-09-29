"""Telemetry hooks for mapping pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping


@dataclass(slots=True)
class MappingTelemetry:
    """Emits metrics and audit events to the logging system."""

    logger: logging.Logger

    def emit_metrics(self, metrics: Mapping[str, float]) -> None:
        self.logger.info("mapping.metrics", extra={"metrics": metrics})

    def emit_event(self, name: str, payload: Mapping[str, object]) -> None:
        self.logger.info(name, extra={"payload": payload})

