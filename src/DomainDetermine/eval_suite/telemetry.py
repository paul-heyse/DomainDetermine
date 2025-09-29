"""Telemetry helpers for evaluation suites."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping


@dataclass(slots=True)
class EvalSuiteTelemetry:
    """Emits audit-friendly telemetry for evaluation runs."""

    logger: logging.Logger

    def emit_manifest_event(self, manifest_hash: str, payload: Mapping[str, object]) -> None:
        self.logger.info(
            "eval_suite.manifest",
            extra={"manifest_hash": manifest_hash, "payload": payload},
        )

    def emit_result_metrics(self, metrics: Mapping[str, Mapping[str, float]]) -> None:
        self.logger.info("eval_suite.metrics", extra={"metrics": metrics})

    def emit_alert(self, alert_type: str, payload: Mapping[str, object]) -> None:
        self.logger.warning(
            "eval_suite.alert",
            extra={"alert_type": alert_type, "payload": payload},
        )


