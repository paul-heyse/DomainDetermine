from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import pytest

from DomainDetermine.kos_ingestion.models import (
    ConnectorContext,
    LicensingPolicy,
    SourceConfig,
    SourceType,
)
from DomainDetermine.kos_ingestion.pipeline import IngestConnector
from DomainDetermine.kos_ingestion.validation import ValidationResult


@pytest.fixture
def artifact_root(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def context(artifact_root: Path) -> ConnectorContext:
    policy = LicensingPolicy(name="test", allow_raw_exports=False, restricted_fields={"pref_label"})
    (artifact_root / "reviews.json").write_text(
        json.dumps({"local": {"reviewer": "alice", "status": "approved"}}),
        encoding="utf-8",
    )
    return ConnectorContext(artifact_root=artifact_root, policies={"test": policy})


def test_validation_result_severity_levels() -> None:
    passed = ValidationResult(shacl={"status": "passed"}, tabular={"status": "passed"}, diagnostics={"summary": {}})
    needs_review = ValidationResult(
        shacl={"status": "passed"},
        tabular={"status": "passed"},
        diagnostics={"summary": {"duplicate_labels": 1}},
    )
    blocker = ValidationResult(shacl={"status": "failed"}, tabular={"status": "passed"}, diagnostics={"summary": {}})

    assert passed.to_dict()["severity"] == "passed"
    assert needs_review.to_dict()["severity"] == "needs_review"
    assert blocker.to_dict()["severity"] == "blocker"


def _write_skos(tmp_path: Path, alt_labels: Sequence[str] = ()) -> Path:
    lines = ["@prefix skos: <http://www.w3.org/2004/02/skos/core#> .", "<http://example.com/A> skos:prefLabel \"Concept A\"@en ."]
    for label in alt_labels:
        lines.append(f"<http://example.com/A> skos:altLabel \"{label}\"@en .")
    path = tmp_path / "local.ttl"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _run_ingest(tmp_path: Path, context: ConnectorContext, *, alt_labels: Sequence[str] = ()):
    source_path = _write_skos(tmp_path, alt_labels)
    config = SourceConfig(id="local", type=SourceType.SKOS, location=str(source_path), license_name="test")
    connector = IngestConnector(context=context)
    return connector.run(config)


def test_ingest_summary_marked_passed(tmp_path: Path, context: ConnectorContext) -> None:
    result = _run_ingest(tmp_path, context)
    validation = result.metadata.extra["validation"]
    assert validation["severity"] == "passed"

    run_summary_path = context.artifact_root / "local" / "run.json"
    summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    assert summary["validation_severity"] == "passed"
    assert summary["license"]["export_allowed"] is False


def test_ingest_summary_marks_duplicate_labels(tmp_path: Path, context: ConnectorContext) -> None:
    result = _run_ingest(tmp_path, context, alt_labels=("Concept A", "Concept A"))
    validation = result.metadata.extra["validation"]
    assert validation["severity"] == "needs_review"
    diagnostics = validation["diagnostics"]["summary"]
    assert diagnostics["duplicate_labels"] == 1

    run_summary_path = context.artifact_root / "local" / "run.json"
    summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    assert summary["validation_severity"] == "needs_review"
