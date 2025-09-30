"""Dashboard and alerting utilities for prompt-pack quality metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Sequence

from DomainDetermine.governance.event_log import (
    GovernanceEventLog,
    log_prompt_quality_alert,
)
from DomainDetermine.governance.models import ArtifactRef

from .metrics import MetricsRepository
from .quality import YardstickRegistry


@dataclass(frozen=True)
class Alert:
    """Represents a quality regression notification."""

    template_id: str
    version: str
    locale: str
    metric: str
    severity: str
    value: float
    threshold: float
    occurrences: int
    message: str


class QualityDashboard:
    """Render aggregated metric snapshots for dashboards."""

    def __init__(self, metrics: MetricsRepository, yardsticks: YardstickRegistry) -> None:
        self._metrics = metrics
        self._yardsticks = yardsticks

    def build_snapshot(self) -> Mapping[str, object]:
        payload: Dict[str, object] = {}
        for key, entry in self._metrics.as_dict().items():
            template_id = entry["template_id"]
            version = entry["version"]
            try:
                yardstick = self._yardsticks.get(template_id, version)
                yardstick_payload = yardstick.as_dict()
            except KeyError:
                yardstick_payload = None
            payload[key] = {
                "template_id": template_id,
                "version": version,
                "locales": entry["locales"],
                "yardstick": yardstick_payload,
            }
        return payload


class AlertManager:
    """Evaluate metrics against yardsticks and emit governance alerts."""

    def __init__(
        self,
        yardsticks: YardstickRegistry,
        *,
        consecutive_threshold: int = 2,
        governance_log: GovernanceEventLog | None = None,
        governance_actor: str = "prompt-quality-monitor",
    ) -> None:
        self._yardsticks = yardsticks
        self._consecutive_threshold = max(1, consecutive_threshold)
        self._violations: Dict[tuple[str, str, str, str], int] = {}
        self._governance_log = governance_log
        self._governance_actor = governance_actor

    def evaluate(self, metrics: MetricsRepository) -> Sequence[Alert]:
        alerts: list[Alert] = []
        snapshot = metrics.as_dict()
        for key, entry in snapshot.items():
            template_id = entry["template_id"]
            version = entry["version"]
            try:
                yardstick = self._yardsticks.get(template_id, version)
            except KeyError:
                continue
            for locale, values in entry["locales"].items():
                locale_alerts = list(
                    self._evaluate_locale(
                        template_id,
                        version,
                        locale,
                        values,
                        yardstick.minimums,
                        yardstick.maximums,
                    )
                )
                for alert in locale_alerts:
                    self._emit_governance_alert(alert)
                alerts.extend(locale_alerts)
        return alerts

    def build_governance_payload(self, alert: Alert) -> Mapping[str, object]:
        return {
            "channel": "prompt-pack-governance",
            "review_task": {
                "title": f"Investigate {alert.metric} regression for {alert.template_id}:{alert.version}",
                "severity": alert.severity,
                "details": {
                    "metric": alert.metric,
                    "value": alert.value,
                    "threshold": alert.threshold,
                    "locale": alert.locale,
                    "occurrences": alert.occurrences,
                },
            },
        }

    def _evaluate_locale(
        self,
        template_id: str,
        version: str,
        locale: str,
        values: Mapping[str, float],
        minimums: Mapping[str, float],
        maximums: Mapping[str, float],
    ) -> Iterable[Alert]:
        found: list[Alert] = []
        for metric, threshold in minimums.items():
            value = values.get(metric)
            if value is None:
                continue
            key = (template_id, version, locale, metric)
            if value < threshold:
                count = self._violations.get(key, 0) + 1
                self._violations[key] = count
                if count >= self._consecutive_threshold:
                    found.append(
                        Alert(
                            template_id=template_id,
                            version=version,
                            locale=locale,
                            metric=metric,
                            severity="critical",
                            value=value,
                            threshold=threshold,
                            occurrences=count,
                            message=(
                                f"{metric} fell below yardstick ({value:.3f} < {threshold:.3f})"
                            ),
                        ),
                    )
                    self._violations[key] = 0
            else:
                self._violations[key] = 0
        for metric, threshold in maximums.items():
            value = values.get(metric)
            if value is None:
                continue
            key = (template_id, version, locale, metric)
            if value > threshold:
                count = self._violations.get(key, 0) + 1
                self._violations[key] = count
                if count >= self._consecutive_threshold:
                    found.append(
                        Alert(
                            template_id=template_id,
                            version=version,
                            locale=locale,
                            metric=metric,
                            severity="critical",
                            value=value,
                            threshold=threshold,
                            occurrences=count,
                            message=(
                                f"{metric} exceeded yardstick ({value:.3f} > {threshold:.3f})"
                            ),
                        ),
                    )
                    self._violations[key] = 0
            else:
                self._violations[key] = 0
        return found

    # ----------------------------------------------------------------- helpers
    def _emit_governance_alert(self, alert: Alert) -> None:
        if not self._governance_log:
            return
        artifact = ArtifactRef(
            artifact_id=alert.template_id,
            version=alert.version,
            hash="unknown",
        )
        payload = {
            "metric": alert.metric,
            "value": alert.value,
            "threshold": alert.threshold,
            "locale": alert.locale,
            "occurrences": alert.occurrences,
            "message": alert.message,
        }
        log_prompt_quality_alert(
            self._governance_log,
            artifact=artifact,
            actor=self._governance_actor,
            payload=payload,
        )


__all__ = [
    "Alert",
    "AlertManager",
    "QualityDashboard",
]
