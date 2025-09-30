"""Tests for prompt pack quality helpers."""

from __future__ import annotations

import json
from pathlib import Path

from DomainDetermine.prompt_pack.metrics import MetricsRepository, TemplateMetrics
from DomainDetermine.prompt_pack.quality import (
    DEFAULT_YARDSTICKS,
    AcceptanceYardstick,
    YardstickRegistry,
)


def test_acceptance_yardstick_evaluation_pass() -> None:
    yardstick = AcceptanceYardstick(
        template_id="mapping_decision",
        version="1.0.0",
        minimums={"grounding_fidelity": 0.9},
        maximums={"hallucination_rate": 0.05},
    )
    metrics = {"grounding_fidelity": 0.95, "hallucination_rate": 0.01}
    assert yardstick.evaluate(metrics) is True


def test_acceptance_yardstick_evaluation_fail() -> None:
    yardstick = AcceptanceYardstick(
        template_id="mapping_decision",
        version="1.0.0",
        minimums={"grounding_fidelity": 0.9},
        maximums={"hallucination_rate": 0.05},
    )
    metrics = {"grounding_fidelity": 0.85, "hallucination_rate": 0.07}
    assert yardstick.evaluate(metrics) is False


def test_yardstick_registry_lookup_and_evaluate() -> None:
    registry = YardstickRegistry()
    registry.register(
        AcceptanceYardstick(
            template_id="mapping_decision",
            version="1.0.0",
            minimums={"grounding_fidelity": 0.9},
            maximums={"hallucination_rate": 0.05},
        )
    )
    metrics = TemplateMetrics(template_id="mapping_decision", version="1.0.0")
    metrics.record("grounding_fidelity", 0.93)
    metrics.record("hallucination_rate", 0.01)
    assert registry.evaluate(metrics) is True


def test_default_yardstick_registry_contains_mapping_decision() -> None:
    metrics = TemplateMetrics(template_id="mapping_decision", version="1.0.0")
    metrics.record("grounding_fidelity", 0.95)
    metrics.record("citation_coverage", 0.97)
    metrics.record("acceptance_rate", 0.85)
    metrics.record("hallucination_rate", 0.01)
    metrics.record("constraint_violations", 0.0)
    assert DEFAULT_YARDSTICKS.evaluate(metrics) is True


def test_default_yardstick_fails_when_metric_regresses() -> None:
    metrics = TemplateMetrics(template_id="mapping_decision", version="1.0.0")
    metrics.record("grounding_fidelity", 0.88)
    metrics.record("citation_coverage", 0.97)
    metrics.record("acceptance_rate", 0.85)
    metrics.record("hallucination_rate", 0.03)
    metrics.record("constraint_violations", 0.0)
    assert DEFAULT_YARDSTICKS.evaluate(metrics) is False


def test_metrics_repository_snapshot(tmp_path: Path) -> None:
    repo = MetricsRepository()
    repo.get("template", "1.0.0").record("accuracy", 0.95)
    snapshot = repo.as_dict()
    entry = snapshot["template:1.0.0"]
    assert entry["locales"]["default"]["accuracy"] == 0.95


def test_metrics_snapshot_serialization(tmp_path: Path) -> None:
    repo = MetricsRepository()
    metrics = repo.get("template", "1.0.0")
    metrics.record("grounding_fidelity", 0.9)
    output = repo.persist(tmp_path / "metrics.json")
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "template:1.0.0" in data["metrics"]
    assert data["metrics"]["template:1.0.0"]["locales"]["default"]["grounding_fidelity"] == 0.9
