from __future__ import annotations

import json
from pathlib import Path

import pytest

from DomainDetermine.auditor import (
    AuditRunConfig,
    AuditStorage,
    CoverageAuditor,
    GovernanceNotifier,
    PolicyPack,
)


@pytest.fixture()
def coverage_plan() -> list[dict[str, object]]:
    return [
        {
            "concept_id": "C1",
            "branch": "B1",
            "path_to_root": ["root", "B1", "C1"],
            "planned_quota": 50,
            "locale": "US",
            "difficulty": "advanced",
            "policy_flags": ["financial"],
        },
        {
            "concept_id": "C2",
            "branch": "B2",
            "path_to_root": ["root", "B2", "C2"],
            "planned_quota": 50,
            "locale": "EU",
            "difficulty": "basic",
            "policy_flags": ["redacted"],
        },
    ]


@pytest.fixture()
def concept_table() -> list[dict[str, object]]:
    return [
        {
            "concept_id": "C1",
            "is_deprecated": False,
            "path_to_root": ["root", "B1", "C1"],
        },
        {
            "concept_id": "C2",
            "is_deprecated": False,
            "path_to_root": ["root", "B2", "C2"],
        },
    ]


def test_auditor_generates_certificate(
    coverage_plan: list[dict[str, object]],
    concept_table: list[dict[str, object]],
    tmp_path: Path,
) -> None:
    config = AuditRunConfig(
        kos_snapshot_id="kos-v1",
        plan_version="plan-v1",
        audit_run_id="audit-123",
        signer_key_id="test-key",
        policy_pack_version="policy-v1",
        facet_domains={"locale": ["US", "EU"], "difficulty": ["basic", "advanced"]},
    )
    policy_pack = PolicyPack(
        forbidden_concepts=("C999",),
        jurisdiction_rules={"C1": ("US",)},
        licensing_restrictions={"restricted": ("definition",)},
        pii_required_flags=("financial",),
        branch_floors={"B1": 0.1},
        branch_ceilings={"B2": 0.8},
    )
    storage = AuditStorage(tmp_path / "artifacts")
    notifier = GovernanceNotifier(tmp_path / "governance" / "audits.jsonl")
    auditor = CoverageAuditor(
        config,
        policy_pack,
        storage=storage,
        governance_notifier=notifier,
    )
    result = auditor.run(coverage_plan=coverage_plan, concept_table=concept_table)

    assert len(result.audit_dataset) == 2
    assert result.certificate.metadata["audit_run_id"] == "audit-123"
    assert result.certificate.signature
    metric_names = {metric.name for metric in result.metrics}
    assert "branch_entropy" in metric_names
    assert any(finding.status.value == "fail" for finding in result.findings) is False
    assert result.report["executive_summary"]
    assert all("plan_version" in event for event in result.telemetry_events)
    dataset_path = storage.base_path / result.artifact_paths.dataset_uri
    certificate_path = storage.base_path / result.artifact_paths.certificate_uri
    report_path = storage.base_path / result.artifact_paths.report_uri
    assert dataset_path.exists()
    assert certificate_path.exists()
    assert report_path.exists()
    registry_path = notifier.registry_path
    assert registry_path.exists()
    entries = [json.loads(line) for line in registry_path.read_text().splitlines() if line.strip()]
    assert entries and entries[0]["audit_run_id"] == "audit-123"


def test_auditor_flags_forbidden_concepts(
    coverage_plan: list[dict[str, object]],
    concept_table: list[dict[str, object]],
    tmp_path: Path,
) -> None:
    config = AuditRunConfig(
        kos_snapshot_id="kos-v1",
        plan_version="plan-v2",
        audit_run_id="audit-124",
        signer_key_id="test-key",
        policy_pack_version="policy-v1",
    )
    policy_pack = PolicyPack(forbidden_concepts=("C1",))
    storage = AuditStorage(tmp_path / "artifacts")
    notifier = GovernanceNotifier(tmp_path / "governance" / "audits.jsonl")
    auditor = CoverageAuditor(
        config,
        policy_pack,
        storage=storage,
        governance_notifier=notifier,
    )
    result = auditor.run(coverage_plan=coverage_plan, concept_table=concept_table)

    blocking_failures = result.certificate.findings_summary["blocking_failures"]
    assert blocking_failures == 1
    forbidden_events = [
        event for event in result.telemetry_events if event["metric_name"] == "policy_finding"
    ]
    assert forbidden_events
