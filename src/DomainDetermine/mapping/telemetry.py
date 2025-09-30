"""Telemetry hooks for mapping pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping

from DomainDetermine.governance import ArtifactRef, GovernanceEventLog, log_mapping_batch_published


@dataclass(slots=True)
class MappingTelemetry:
    """Emits metrics and audit events to the logging system."""

    logger: logging.Logger
    governance_log: GovernanceEventLog | None = None
    governance_artifact: ArtifactRef | None = None

    def emit_metrics(self, metrics: Mapping[str, float]) -> None:
        enriched = dict(metrics)
        total = metrics.get("items_total", 0.0)
        resolved = metrics.get("items_resolved", 0.0)
        enriched.setdefault("resolution_rate", resolved / total if total else 0.0)
        self.logger.info("mapping.metrics", extra={"metrics": enriched})
        if self.governance_log and self.governance_artifact:
            payload = {
                "metrics": enriched,
            }
            log_mapping_batch_published(
                self.governance_log,
                artifact=self.governance_artifact,
                actor="mapping-pipeline",
                payload=payload,
            )

    def emit_event(self, name: str, payload: Mapping[str, object]) -> None:
        self.logger.info(name, extra={"payload": payload})

    def record_deferral(self, item_id: str, reason: str) -> None:
        self.logger.info(
            "mapping.deferral",
            extra={"payload": {"item_id": item_id, "reason": reason}},
        )

    def record_precision(self, precision_at_1: float, recall_at_k: float, cost_usd: float) -> None:
        self.logger.info(
            "mapping.quality",
            extra={
                "payload": {
                    "precision_at_1": precision_at_1,
                    "recall_at_k": recall_at_k,
                    "cost_usd": cost_usd,
                }
            },
        )


__all__ = ["MappingTelemetry"]

