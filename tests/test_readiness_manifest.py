"""Tests for release manifest generation and registration."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from DomainDetermine.governance.registry import GovernanceRegistry, RegistryConfig
from DomainDetermine.governance.versioning import ChangeImpact, SignatureManager
from DomainDetermine.prompt_pack.registry import PromptManifest, PromptRegistry
from DomainDetermine.readiness.manifest import (
    ApprovalRecord,
    ReleaseArtifact,
    ReleaseManifest,
    generate_release_manifest,
    register_manifest,
    write_manifest,
)


def test_generate_release_manifest_uses_inputs() -> None:
    manifest = generate_release_manifest(
        release="2025.10.02",
        artifacts=[{"name": "service", "version": "1.4.0", "hash": "abc"}],
        scorecard_path="readiness_scorecards/scorecard.json",
        readiness_run_id="run123",
        approvals=[{"role": "approver", "actor": "alice", "timestamp": "2025-10-02T14:30:00Z"}],
        metadata={"environment": "staging"},
    )
    payload = manifest.to_dict()
    assert payload["release"] == "2025.10.02"
    assert payload["scorecard_path"] == "readiness_scorecards/scorecard.json"
    assert payload["readiness_run_id"] == "run123"
    assert payload["metadata"]["environment"] == "staging"
    assert payload["approvals"][0]["actor"] == "alice"
    assert datetime.fromisoformat(payload["generated_at"])


def test_write_and_register_manifest(tmp_path: Path) -> None:
    manifest = ReleaseManifest(
        release="2025.10.02",
        generated_at=datetime.fromisoformat("2025-10-02T12:00:00+00:00"),
        artifacts=(ReleaseArtifact(name="service", version="1.4.0", hash="abc"),),
        scorecard_path="readiness_scorecards/run123.json",
        readiness_run_id="run123",
        approvals=(
            ApprovalRecord(role="approver", actor="alice", timestamp="2025-10-02T14:30:00Z"),
        ),
        rollback_plan={"trigger": "latency_p95>400ms", "steps": ["disable", "rollback"], "rehearsed_at": "2025-09-18T16:00:00Z"},
    )
    manifest_path = write_manifest(manifest, tmp_path / "release-manifest.json")
    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["release"] == "2025.10.02"

    prompt_registry = PromptRegistry()
    prompt_registry.register(
        PromptManifest(
            template_id="mapping_decision",
            version="1.0.0",
            schema_id="mapping_decision_v1",
            policy_id="mapping_decision_v1",
            hash="c6ec246cd099d3e209459247358b00a24bd9aaa0b295a4fb8055c16a50b57d25",
        )
    )
    registry = GovernanceRegistry(
        config=RegistryConfig(artifact_prefixes={"release": "rel"}),
        prompt_registry=prompt_registry,
    )
    registry.signature_manager = SignatureManager(secret="test-secret")
    metadata = register_manifest(
        manifest,
        registry,
        artifact_type="release",
        change_impact=ChangeImpact.MINOR,
        tenant_id="platform",
        license_tag="internal",
        policy_pack_hash="prompt-pack-hash",
        change_reason="readiness-release",
        created_by="ci-bot",
        title="Release 2025.10.02",
        summary="Production readiness manifest",
        dependencies=(),
        reviewers=("governance@example.com",),
        waivers=("waiver-001",),
        environment_fingerprint={"cluster": "prod"},
        prompt_templates=(
            "mapping_decision:1.0.0#c6ec246cd099d3e209459247358b00a24bd9aaa0b295a4fb8055c16a50b57d25",
        ),
    )

    assert metadata.artifact_type == "release"
    assert metadata.approvals == ("alice",)
    assert metadata.environment_fingerprint["cluster"] == "prod"
    assert registry.get(metadata.artifact_id) is not None
