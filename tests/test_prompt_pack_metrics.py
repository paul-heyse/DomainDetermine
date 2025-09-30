"""Tests for prompt pack metrics collection."""

from __future__ import annotations

import json
from pathlib import Path

from DomainDetermine.prompt_pack.metrics import MetricsRepository, TemplateMetrics


def test_metrics_repository_as_dict() -> None:
    repo = MetricsRepository()
    metrics = TemplateMetrics("template", "1.0.0")
    metrics.record("warmup_status", 1.0)
    repo.upsert(metrics)

    snapshot = repo.as_dict()
    assert "template:1.0.0" in snapshot
    entry = snapshot["template:1.0.0"]
    assert entry["template_id"] == "template"
    assert entry["locales"]["default"]["warmup_status"] == 1.0


def test_metrics_repository_persist(tmp_path: Path) -> None:
    repo = MetricsRepository()
    repo.record_metrics(
        template_id="template",
        version="1.0.0",
        metrics={"grounding_fidelity": 0.92},
        locale="en-GB",
        observation=True,
    )
    output = repo.persist(tmp_path / "metrics.json")
    payload = json.loads(output.read_text(encoding="utf-8"))
    entry = payload["metrics"]["template:1.0.0"]
    assert entry["locales"]["en-GB"]["grounding_fidelity"] == 0.92


def test_record_quality_sample_tracks_observations(tmp_path: Path) -> None:
    repo = MetricsRepository()
    repo.record_quality_sample(
        template_id="template",
        version="1.0.0",
        locale="en-GB",
        acceptance_rate=0.82,
        deferral_rate=0.18,
        grounding_fidelity=0.93,
        hallucination_rate=0.01,
        constraint_violations=0.0,
        latency_ms=540.0,
        cost_usd=0.19,
    )
    data = repo.as_dict()["template:1.0.0"]
    history = data["history"]["en-GB"]
    assert history
    sample = history[-1]
    assert sample["acceptance_rate"] == 0.82
    assert sample["latency_ms"] == 540.0
