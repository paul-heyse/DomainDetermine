"""Tests for readiness gate evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from DomainDetermine.readiness.gate import GateError, evaluate_gate
from DomainDetermine.readiness.manifest import generate_release_manifest, write_manifest


def _write_manifest(path: Path, *, rehearsed_at: datetime | None = None, approvals=None) -> Path:
    manifest = generate_release_manifest(
        release="2025.10.02",
        artifacts=[{"name": "service", "version": "1.4.0", "hash": "abc"}],
        scorecard_path="scorecard.json",
        readiness_run_id="run123",
        approvals=approvals or [
            {"role": "change-board", "actor": "alice", "timestamp": "2025-10-02T14:00:00Z"}
        ],
        rollback_plan={
            "trigger": "latency_p95>400ms",
            "steps": ["disable", "rollback"],
            "rehearsed_at": rehearsed_at.isoformat() if rehearsed_at else "",
        },
    )
    return write_manifest(manifest, path)


def _write_config(path: Path, **overrides) -> Path:
    config = {
        "enforce_approvals": True,
        "required_roles": ["change-board"],
        "require_rehearsal": True,
        "max_rehearsal_age_days": 30,
        "disallow_waivers": False,
    }
    config.update(overrides)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_evaluate_gate_pass(tmp_path: Path) -> None:
    manifest_path = _write_manifest(
        tmp_path / "manifest.json",
        rehearsed_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    config_path = _write_config(tmp_path / "gate.yml")
    evaluate_gate(manifest_path, config_path=config_path, release_id="rel-123")


def test_evaluate_gate_missing_approval(tmp_path: Path) -> None:
    manifest = generate_release_manifest(
        release="2025.10.02",
        artifacts=[{"name": "service", "version": "1.4.0", "hash": "abc"}],
        scorecard_path="scorecard.json",
        readiness_run_id="run123",
        approvals=[],
        rollback_plan={
            "trigger": "latency_p95>400ms",
            "steps": [],
            "rehearsed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    manifest_path = write_manifest(manifest, tmp_path / "manifest.json")
    config_path = _write_config(tmp_path / "gate.yml", enforce_approvals=True)
    with pytest.raises(GateError):
        evaluate_gate(manifest_path, config_path=config_path)


def test_evaluate_gate_stale_rehearsal(tmp_path: Path) -> None:
    old_date = datetime.now(timezone.utc) - timedelta(days=45)
    manifest_path = _write_manifest(tmp_path / "manifest.json", rehearsed_at=old_date)
    config_path = _write_config(tmp_path / "gate.yml", max_rehearsal_age_days=30)
    with pytest.raises(GateError):
        evaluate_gate(manifest_path, config_path=config_path)

