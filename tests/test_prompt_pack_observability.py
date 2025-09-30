"""Tests for prompt pack observability helpers."""

from __future__ import annotations

from pathlib import Path

from DomainDetermine.governance.event_log import GovernanceEventLog, GovernanceEventType
from DomainDetermine.prompt_pack.metrics import MetricsRepository
from DomainDetermine.prompt_pack.observability import AlertManager, QualityDashboard
from DomainDetermine.prompt_pack.quality import AcceptanceYardstick, YardstickRegistry


def _yardsticks() -> YardstickRegistry:
    registry = YardstickRegistry()
    registry.register(
        AcceptanceYardstick(
            template_id="template",
            version="1.0.0",
            minimums={"grounding_fidelity": 0.9},
            maximums={"hallucination_rate": 0.02},
        )
    )
    return registry


def test_dashboard_snapshot_contains_yardstick() -> None:
    repo = MetricsRepository()
    yardsticks = _yardsticks()
    repo.record_metrics(
        template_id="template",
        version="1.0.0",
        metrics={"grounding_fidelity": 0.95, "hallucination_rate": 0.0},
    )
    dashboard = QualityDashboard(repo, yardsticks)
    snapshot = dashboard.build_snapshot()
    entry = snapshot["template:1.0.0"]
    assert entry["yardstick"]["minimums"]["grounding_fidelity"] == 0.9
    assert entry["locales"]["default"]["grounding_fidelity"] == 0.95


def test_alert_manager_emits_after_consecutive_regressions(tmp_path: Path) -> None:
    repo = MetricsRepository()
    yardsticks = _yardsticks()
    event_log = GovernanceEventLog(tmp_path / "events.jsonl", secret="test")
    manager = AlertManager(yardsticks, consecutive_threshold=2, governance_log=event_log)

    repo.record_metrics(
        template_id="template",
        version="1.0.0",
        metrics={"grounding_fidelity": 0.85, "hallucination_rate": 0.01},
    )
    assert manager.evaluate(repo) == []

    repo.record_metrics(
        template_id="template",
        version="1.0.0",
        metrics={"grounding_fidelity": 0.84, "hallucination_rate": 0.03},
    )
    alerts = manager.evaluate(repo)
    assert alerts
    alert = alerts[0]
    assert alert.metric in {"grounding_fidelity", "hallucination_rate"}
    payload = manager.build_governance_payload(alert)
    assert payload["review_task"]["severity"] == "critical"

    events = list(event_log.query())
    assert events
    assert any(event.event_type is GovernanceEventType.PROMPT_QUALITY_ALERT for event in events)
