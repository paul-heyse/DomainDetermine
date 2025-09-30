"""Tests for prompt pack governance version tooling."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from DomainDetermine.governance.event_log import GovernanceEventLog, GovernanceEventType
from DomainDetermine.governance.versioning import ChangeImpact
from DomainDetermine.prompt_pack.registry import PromptManifest, PromptRegistry, PromptRegistryError
from DomainDetermine.prompt_pack.versioning import PromptVersionManager


def _write_prompt_assets(root: Path, *, version: str) -> None:
    templates_dir = root / "templates" / "mapping_decision"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "prompt.j2").write_text("{{ context_json }}", encoding="utf-8")
    metadata = {
        "template_id": "mapping_decision",
        "version": version,
        "schema": "mapping_decision_v1",
        "policy": "mapping_decision_v1",
        "description": "test",
    }
    (templates_dir / "prompt.json").write_text(json.dumps(metadata), encoding="utf-8")
    schema_dir = root / "schemas"
    schema_dir.mkdir(exist_ok=True)
    (schema_dir / "mapping_decision_v1.schema.json").write_text(
        json.dumps({"type": "object"}),
        encoding="utf-8",
    )
    policy_dir = root / "policies"
    policy_dir.mkdir(exist_ok=True)
    policy = {
        "allowed_sources": ["concept_definition"],
        "token_budget": {"prompt": 2048, "completion": 256},
        "citation_policy": {"require_citations": True},
    }
    (policy_dir / "mapping_decision_v1.policy.json").write_text(json.dumps(policy), encoding="utf-8")


def test_publish_records_changelog_and_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompt_root = tmp_path / "prompt_pack"
    _write_prompt_assets(prompt_root, version="1.0.0")
    changelog_path = tmp_path / "CHANGELOG.md"
    journal_path = tmp_path / "releases.jsonl"
    event_log_path = tmp_path / "events.jsonl"
    monkeypatch.setenv("GOVERNANCE_EVENT_SECRET", "secret")

    prompt_registry = PromptRegistry()
    event_log = GovernanceEventLog(event_log_path)
    manager = PromptVersionManager(
        prompt_root,
        prompt_registry,
        changelog_path=changelog_path,
        journal_path=journal_path,
        event_log=event_log,
    )

    manifest = manager.publish(
        "mapping_decision",
        impact=ChangeImpact.MAJOR,
        rationale="initial publish",
        owners=["governance@example.com"],
        expected_metrics={"grounding_fidelity": 0.02},
        approvals=["approver"],
        actor="ci-user",
        related_manifests=["rel-000001"],
    )

    assert manifest.version == "1.0.0"
    assert prompt_registry.get("mapping_decision", "1.0.0").hash == manifest.hash
    changelog = changelog_path.read_text(encoding="utf-8")
    assert "mapping_decision 1.0.0" in changelog
    journal_lines = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines() if line]
    assert journal_lines[0]["hash"] == manifest.hash
    events = list(event_log.query(artifact_id="mapping_decision"))
    assert events[0].event_type is GovernanceEventType.PROMPT_PUBLISHED
    assert events[0].payload["related_manifests"] == ["rel-000001"]
    assert manager.reference(manifest).startswith("mapping_decision:1.0.0#")


def test_publish_rejects_semver_mismatch(tmp_path: Path) -> None:
    prompt_root = tmp_path / "prompt_pack"
    _write_prompt_assets(prompt_root, version="1.1.0")
    prompt_registry = PromptRegistry()
    prompt_registry.register(
        PromptManifest(
            template_id="mapping_decision",
            version="1.0.0",
            schema_id="mapping_decision_v1",
            policy_id="mapping_decision_v1",
            hash="prev-hash",
        )
    )
    manager = PromptVersionManager(prompt_root, prompt_registry)

    with pytest.raises(PromptRegistryError):
        manager.publish(
            "mapping_decision",
            impact=ChangeImpact.MAJOR,
            rationale="incorrect bump",
            owners=["owner"],
        )


def test_record_rollback_and_waiver(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOVERNANCE_EVENT_SECRET", "secret")
    prompt_registry = PromptRegistry()
    prompt_manifest = PromptManifest(
        template_id="mapping_decision",
        version="1.0.0",
        schema_id="mapping_decision_v1",
        policy_id="mapping_decision_v1",
        hash="abc123",
    )
    prompt_registry.register(prompt_manifest)
    event_log = GovernanceEventLog(tmp_path / "events.jsonl")
    manager = PromptVersionManager(
        tmp_path / "unused",
        prompt_registry,
        event_log=event_log,
    )

    manager.record_rollback(
        "mapping_decision",
        "1.0.0",
        actor="approver",
        reason="regression",
        waiver_id="waiver-123",
    )
    manager.record_waiver(
        "mapping_decision",
        "1.0.0",
        actor="governance",
        justification="metrics under review",
        expiry="2025-10-30",
    )

    events = list(event_log.query(artifact_id="mapping_decision"))
    assert events[0].event_type is GovernanceEventType.PROMPT_ROLLED_BACK
    assert events[0].payload["waiver_id"] == "waiver-123"
    assert events[1].event_type is GovernanceEventType.WAIVER_GRANTED
    assert events[1].payload["expiry"] == "2025-10-30"
