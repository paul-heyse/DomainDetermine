"""Tests for prompt pack calibration manifests and datasets."""

from __future__ import annotations

from pathlib import Path

import pytest

from DomainDetermine.prompt_pack.calibration import (
    get_calibration_set,
    load_calibration_dataset,
    load_calibration_manifest,
)


def test_load_calibration_manifest(tmp_path: Path) -> None:
    manifest = load_calibration_manifest("mapping_decision", "1.0.0")
    assert manifest.template_id == "mapping_decision"
    assert manifest.version == "1.0.0"
    assert manifest.dataset_path.exists()
    assert manifest.reviewers
    assert manifest.approvals
    assert manifest.license_tag == "internal-use-only"


def test_load_calibration_dataset_examples() -> None:
    dataset = load_calibration_dataset("mapping_decision", "1.0.0")
    examples = tuple(dataset.calibration_set)
    assert len(examples) >= 2
    first = examples[0]
    assert "Competition" in first.input_payload["concept_definition"]
    assert first.expected_output["concept_id"] == "EV:1"


def test_manifest_checksum_validation(tmp_path: Path) -> None:
    root = tmp_path / "prompt_pack" / "calibration" / "test_template" / "1.0.0"
    root.mkdir(parents=True, exist_ok=True)
    dataset_path = root / "examples.jsonl"
    dataset_path.write_text("{}\n", encoding="utf-8")
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        "{""template_id"": ""test_template"", ""version"": ""1.0.0"", ""dataset_path"": ""examples.jsonl"", ""reviewers"": [""qa""], ""approvals"": [""approver""], ""checksum"": ""deadbeef"", ""license"": ""internal"", ""last_reviewed_at"": ""2025-01-01T00:00:00+00:00""}",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_calibration_manifest("test_template", "1.0.0", root=tmp_path / "prompt_pack" / "calibration")


def test_get_calibration_set_uses_registry() -> None:
    calibration_set = get_calibration_set("mapping_decision", "1.0.0")
    assert calibration_set.template_id == "mapping_decision"
    assert calibration_set.version == "1.0.0"
    assert len(tuple(calibration_set)) >= 2

