from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src/DomainDetermine"
if "DomainDetermine" not in sys.modules:
    module = types.ModuleType("DomainDetermine")
    module.__path__ = [str(ROOT)]
    sys.modules["DomainDetermine"] = module

from DomainDetermine.governance.diffs import (  # noqa: E402
    DiffEngine,
    DiffResult,
    DiffStorage,
)


def test_coverage_plan_diff_detects_fairness_alert(tmp_path: Path) -> None:
    engine = DiffEngine(thresholds={"coverage_plan": {"max_fairness_delta": 0.01}})
    old = {
        "strata": [
            {"id": "s1", "branch": "b1", "quota": 10},
            {"id": "s2", "branch": "b2", "quota": 20},
        ],
        "metrics": {"entropy": 0.70, "gini": 0.10},
    }
    new = {
        "strata": [
            {"id": "s1", "branch": "b1", "quota": 20},
            {"id": "s2", "branch": "b2", "quota": 5},
            {"id": "s3", "branch": "b3", "quota": 5},
        ],
        "metrics": {"entropy": 0.90, "gini": 0.18},
    }
    diff = engine.generate_diff("coverage_plan", old, new)
    assert diff.status == "block"
    assert diff.machine_readable["alerts"][0]["type"] == "fairness_drift"

    storage = DiffStorage(tmp_path)
    paths = storage.persist("coverage-plan", "1.1.0", diff)
    machine_content = json.loads(Path(paths["machine"]).read_text())
    assert machine_content["status"] == "block"
    assert "Coverage Plan Diff" in Path(paths["summary"]).read_text()


def test_diff_engine_handles_multiple_artifacts() -> None:
    engine = DiffEngine()
    diff = engine.generate_diff(
        "eval_suite",
        {"slices": ["a", "b"], "thresholds": {"score": 0.5}},
        {"slices": ["a", "c"], "thresholds": {"score": 0.7}},
    )
    assert diff.machine_readable["added_slices"] == ["c"]
    assert diff.machine_readable["removed_slices"] == ["b"]
    assert diff.machine_readable["threshold_changes"]["score"] == pytest.approx(0.2)
    prompt_diff = engine.generate_diff(
        "prompt_pack",
        {"templates": ["t1"], "retrieval_policy": "policy-a"},
        {"templates": ["t1", "t2"], "retrieval_policy": "policy-b"},
    )
    assert prompt_diff.machine_readable["added_templates"] == ["t2"]
    assert prompt_diff.machine_readable["retrieval_policy_changed"]


def test_diff_storage_sanitizes_paths(tmp_path: Path) -> None:
    storage = DiffStorage(tmp_path)
    diff = DiffResult(
        artifact_type="coverage_plan",
        machine_readable={},
        summary_markdown="# Summary",
        status="pass",
    )
    paths = storage.persist("tenant:coverage/plan", "1.0.0+meta", diff)
    machine_path = Path(paths["machine"])
    summary_path = Path(paths["summary"])
    assert machine_path.exists()
    assert summary_path.exists()
    assert ":" not in machine_path.parts[-3]
