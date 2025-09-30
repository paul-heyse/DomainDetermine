"""Governance registry integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from DomainDetermine.governance.event_log import GovernanceEventLog, GovernanceEventType
from DomainDetermine.governance.models import ArtifactMetadata
from DomainDetermine.governance.registry import GovernanceRegistry, RegistryConfig, RegistryError
from DomainDetermine.governance.telemetry import GovernanceTelemetry
from DomainDetermine.governance.versioning import (
    ChangeImpact,
    SignatureManager,
    compute_hash,
    manifest_payload,
)
from DomainDetermine.prompt_pack.registry import (
    PromptManifest,
    PromptRegistry,
    format_prompt_reference,
)

PROMPT_HASH = "c6ec246cd099d3e209459247358b00a24bd9aaa0b295a4fb8055c16a50b57d25"


def _manifest(artifact_id: str, version: str) -> ArtifactMetadata:
    return ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type="mapping",
        version=version,
        hash="",
        signature="sig",
        title="Mapping Records",
        summary="Test",
        tenant_id="tenant",
        license_tag="internal",
        policy_pack_hash="hash",
        change_reason="test",
        created_by="user",
    )


def test_register_and_list() -> None:
    config = RegistryConfig(artifact_prefixes={"mapping": "map"})
    registry = GovernanceRegistry(config=config)
    artifact_id = registry.assign_identifier("mapping")
    signature_manager = SignatureManager(secret="secret")
    manifest = _manifest(artifact_id, "1.0.0")
    manifest.hash = compute_hash(manifest_payload(manifest))
    manifest.signature = signature_manager.sign(
        manifest.hash,
        context=(manifest.artifact_id, manifest.version),
    )
    registry.register(
        artifact_type="mapping",
        metadata=manifest,
        impact=ChangeImpact.MAJOR,
    )
    results = list(registry.list_by_type("mapping"))
    assert len(results) == 1
    assert results[0].artifact_id == artifact_id


def _prompt_registry() -> PromptRegistry:
    registry = PromptRegistry()
    registry.register(
        PromptManifest(
            template_id="mapping_decision",
            version="1.0.0",
            schema_id="mapping_decision_v1",
            policy_id="mapping_decision_v1",
            hash=PROMPT_HASH,
        )
    )
    return registry


def test_register_requires_prompt_reference_match() -> None:
    config = RegistryConfig(artifact_prefixes={"mapping": "map"})
    prompt_registry = _prompt_registry()
    registry = GovernanceRegistry(
        config=config,
        prompt_registry=prompt_registry,
    )
    registry.signature_manager = SignatureManager(secret="secret")
    artifact_id = registry.assign_identifier("mapping")
    manifest = _manifest(artifact_id, "1.0.0")
    prompt_manifest = prompt_registry.resolve("mapping_decision", "1.0.0")
    manifest.prompt_templates = (format_prompt_reference(prompt_manifest),)
    manifest.hash = compute_hash(manifest_payload(manifest))
    manifest.signature = registry.signature_manager.sign(
        manifest.hash,
        context=(manifest.artifact_id, manifest.version),
    )
    stored = registry.register(
        artifact_type="mapping",
        metadata=manifest,
        impact=ChangeImpact.MAJOR,
    )
    assert stored.prompt_templates == manifest.prompt_templates


def test_register_rejects_unknown_prompt_reference() -> None:
    config = RegistryConfig(artifact_prefixes={"mapping": "map"})
    registry = GovernanceRegistry(
        config=config,
        prompt_registry=_prompt_registry(),
    )
    manifest = _manifest("map-000001", "1.0.0")
    manifest.prompt_templates = ("mapping_decision:1.0.0#deadbeef",)
    manifest.hash = compute_hash(manifest_payload(manifest))
    with pytest.raises(RegistryError):
        registry.register(
            artifact_type="mapping",
            metadata=manifest,
            impact=ChangeImpact.MAJOR,
        )


def test_assign_identifier_uses_prefix() -> None:
    config = RegistryConfig(artifact_prefixes={"overlay": "ov"})
    registry = GovernanceRegistry(config=config)
    identifier = registry.assign_identifier("overlay")
    assert identifier.startswith("ov-")


def test_registry_notifies_readiness_dashboards(tmp_path: Path) -> None:
    config = RegistryConfig(artifact_prefixes={"mapping": "map"})
    signature_manager = SignatureManager(secret="secret")
    registry = GovernanceRegistry(config=config, signature_manager=signature_manager)
    registry.attach_event_log(
        GovernanceEventLog(tmp_path / "events.log", secret="secret")
    )
    telemetry = GovernanceTelemetry()
    registry.attach_telemetry(telemetry)

    artifact_id = registry.assign_identifier("mapping")
    manifest = _manifest(artifact_id, "1.0.0")
    manifest.hash = compute_hash(manifest_payload(manifest))
    manifest.signature = signature_manager.sign(
        manifest.hash,
        context=(manifest.artifact_id, manifest.version),
    )

    registry.register(
        artifact_type="mapping",
        metadata=manifest,
        impact=ChangeImpact.MAJOR,
    )

    notifications = list(telemetry.readiness_notifications())
    assert notifications, "expected registry notifications to feed readiness dashboards"
    latest = notifications[-1]
    assert latest["event_type"] == GovernanceEventType.PUBLISH_COMPLETED.value
    assert latest["artifact_id"] == artifact_id
    assert latest["payload"]["artifact_type"] == "mapping"
