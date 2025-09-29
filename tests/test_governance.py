from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src/DomainDetermine"
if "DomainDetermine" not in sys.modules:
    module = types.ModuleType("DomainDetermine")
    module.__path__ = [str(ROOT)]
    sys.modules["DomainDetermine"] = module

from DomainDetermine.governance import (  # noqa: E402
    AccessManager,
    ArtifactRef,
    BackupCoordinator,
    GovernanceEvent,
    GovernanceEventLog,
    GovernanceEventType,
    GovernanceTelemetry,
    LicensePolicy,
    Role,
    TenantPolicy,
)


def test_governance_event_log_roundtrip(tmp_path: Path) -> None:
    log = GovernanceEventLog(tmp_path / "events.jsonl", secret="secret")
    artifact = ArtifactRef(artifact_id="coverage-plan:v1", version="1.0.0", hash="abc123")
    original = GovernanceEvent(
        event_type=GovernanceEventType.PUBLISH_COMPLETED,
        artifact=artifact,
        actor="approver-1",
        payload={"notes": "published"},
    )
    signed = log.append(original)
    assert signed.signature is not None

    queried = list(log.query(artifact_id="coverage-plan:v1"))
    assert len(queried) == 1
    assert queried[0].signature == signed.signature


def test_governance_telemetry_metrics() -> None:
    telemetry = GovernanceTelemetry()
    proposed = datetime(2024, 1, 1, tzinfo=timezone.utc)
    telemetry.record_publish(
        proposed_at=proposed,
        published_at=proposed + timedelta(hours=5),
    )
    telemetry.record_audit_failure(artifact_id="a1", reason="fairness")
    telemetry.record_rollback(artifact_id="a1")
    telemetry.record_registry_latency(120.0)

    snapshot = telemetry.metrics_snapshot()
    assert snapshot["publish_lead_time_avg"] == pytest.approx(5 * 3600)
    assert snapshot["audit_failure_count"] == 1
    assert snapshot["rollback_count"] == 1


def test_access_manager_roles_tenancy_and_license() -> None:
    manager = AccessManager()
    manager.assign_role("alice", Role.APPROVER)
    manager.set_tenant_policy("artifact-1", TenantPolicy(tenant_id="tenant-a", shared_with=("tenant-b",)))
    manager.set_license_policy("artifact-1", LicensePolicy(license_tag="restricted", export_policy="ids_only"))

    decision = manager.check_access(
        user="alice",
        tenant_id="tenant-b",
        required_roles=(Role.APPROVER,),
        artifact_id="artifact-1",
        export_type="ids_only",
    )
    assert decision.allowed

    denied = manager.check_access(
        user="alice",
        tenant_id="tenant-c",
        required_roles=(Role.APPROVER,),
        artifact_id="artifact-1",
        export_type="labels",
    )
    assert not denied.allowed
    assert denied.reason in {"tenant_denied", "license_denied"}


def test_backup_coordinator_records_manifests(tmp_path: Path) -> None:
    coordinator = BackupCoordinator(tmp_path / "backups")
    manifest = coordinator.record_backup(
        backup_id="backup-001",
        artifacts=("artifact-1", "artifact-2"),
        replication_targets=("region-a", "region-b"),
        verification_hash="deadbeef",
    )
    report = coordinator.integrity_report()
    assert report["count"] == 1
    file_path = tmp_path / "backups" / "backup-001.json"
    assert file_path.exists()
    content = json.loads(file_path.read_text())
    assert content["verification_hash"] == manifest.verification_hash


def test_backup_last_backup_orders_by_timestamp(tmp_path: Path) -> None:
    coordinator = BackupCoordinator(tmp_path / "backups")
    first = coordinator.record_backup(
        backup_id="backup-10",
        artifacts=("artifact-1",),
        replication_targets=("region-a",),
        verification_hash="first",
    )
    second = coordinator.record_backup(
        backup_id="backup-2",
        artifacts=("artifact-2",),
        replication_targets=("region-a",),
        verification_hash="second",
    )
    last = coordinator.last_backup()
    assert last is not None
    assert last.verification_hash == second.verification_hash
    assert last.verification_hash != first.verification_hash


def test_event_log_requires_secret(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        GovernanceEventLog(tmp_path / "events.jsonl")

    artifact = ArtifactRef(artifact_id="coverage", version="1", hash="abc")
    log_a = GovernanceEventLog(tmp_path / "events_a.jsonl", secret="secret-a")
    log_b = GovernanceEventLog(tmp_path / "events_b.jsonl", secret="secret-b")

    event = GovernanceEvent(
        event_type=GovernanceEventType.PROPOSAL_CREATED,
        artifact=artifact,
        actor="user",
    )
    signed_a = log_a.append(event)
    signed_b = log_b.append(event)
    assert signed_a.signature != signed_b.signature


import pytest  # noqa: E402  (import needed for approx)
