"""Tests for governance versioning utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from DomainDetermine.governance.models import ArtifactMetadata, ArtifactRef
from DomainDetermine.governance.registry import GovernanceRegistry, RegistryConfig, RegistryError
from DomainDetermine.governance.versioning import (
    ChangeImpact,
    SemanticVersioner,
    SignatureManager,
    compute_hash,
    manifest_payload,
)


def _metadata(artifact_id: str, version: str) -> ArtifactMetadata:
    return ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type="coverage_plan",
        version=version,
        hash="",
        signature="",
        title="Coverage Plan",
        summary="Test artifact",
        tenant_id="tenant",
        license_tag="internal",
        policy_pack_hash="hash",
        change_reason="test",
        created_by="user",
    )


def test_semantic_versioner_initial_versions() -> None:
    versioner = SemanticVersioner()
    assert versioner.next_version(None, ChangeImpact.MAJOR) == "1.0.0"
    assert versioner.next_version(None, ChangeImpact.MINOR) == "0.1.0"
    assert versioner.next_version(None, ChangeImpact.PATCH) == "0.0.1"


def test_semantic_versioner_bump_sequence() -> None:
    versioner = SemanticVersioner()
    assert versioner.next_version("1.2.3", ChangeImpact.PATCH) == "1.2.4"
    assert versioner.next_version("1.2.3", ChangeImpact.MINOR) == "1.3.0"
    assert versioner.next_version("1.2.3", ChangeImpact.MAJOR) == "2.0.0"


def test_registry_registers_artifact() -> None:
    config = RegistryConfig(artifact_prefixes={"coverage_plan": "cp"})
    signature_manager = SignatureManager(secret="secret")
    registry = GovernanceRegistry(config=config, signature_manager=signature_manager)
    artifact_id = registry.assign_identifier("coverage_plan")
    metadata = _metadata(artifact_id, "1.0.0")
    metadata.hash = compute_hash(manifest_payload(metadata))
    metadata.signature = signature_manager.sign(
        metadata.hash,
        context=(metadata.artifact_id, metadata.version),
    )
    registry.register(
        artifact_type="coverage_plan",
        metadata=metadata,
        impact=ChangeImpact.MAJOR,
        dependencies=metadata.upstream,
    )
    stored = registry.get(metadata.artifact_id)
    assert stored is not None
    assert stored.version == "1.0.0"


def test_registry_rejects_hash_mismatch() -> None:
    config = RegistryConfig(artifact_prefixes={"coverage_plan": "cp"})
    registry = GovernanceRegistry(config=config)
    artifact_id = registry.assign_identifier("coverage_plan")
    metadata = _metadata(artifact_id, "1.0.0")
    metadata.hash = "invalid"
    with pytest.raises(RegistryError):
        registry.register(
            artifact_type="coverage_plan",
            metadata=metadata,
            impact=ChangeImpact.MAJOR,
            dependencies=metadata.upstream,
        )


def test_registry_validates_dependencies() -> None:
    config = RegistryConfig(artifact_prefixes={"coverage_plan": "cp"})
    registry = GovernanceRegistry(config=config)
    artifact_id = registry.assign_identifier("coverage_plan")
    metadata = _metadata(artifact_id, "1.0.0")
    metadata.hash = compute_hash(manifest_payload(metadata))
    missing_ref = ArtifactRef(artifact_id="missing", version="1.0.0", hash="abc")
    with pytest.raises(RegistryError):
        registry.register(
            artifact_type="coverage_plan",
            metadata=metadata,
            impact=ChangeImpact.MAJOR,
            dependencies=(missing_ref,),
        )


def test_signature_required_when_manager_present() -> None:
    config = RegistryConfig(artifact_prefixes={"coverage_plan": "cp"})
    signature_manager = SignatureManager(secret="secret")
    registry = GovernanceRegistry(config=config, signature_manager=signature_manager)
    artifact_id = registry.assign_identifier("coverage_plan")
    metadata = _metadata(artifact_id, "1.0.0")
    metadata.hash = compute_hash(manifest_payload(metadata))
    metadata.signature = ""
    with pytest.raises(RegistryError):
        registry.register(
            artifact_type="coverage_plan",
            metadata=metadata,
            impact=ChangeImpact.MAJOR,
            dependencies=metadata.upstream,
        )


def test_registry_rejects_invalid_signature() -> None:
    config = RegistryConfig(artifact_prefixes={"coverage_plan": "cp"})
    signature_manager = SignatureManager(secret="secret")
    registry = GovernanceRegistry(config=config, signature_manager=signature_manager)
    artifact_id = registry.assign_identifier("coverage_plan")
    metadata = _metadata(artifact_id, "1.0.0")
    metadata.hash = compute_hash(manifest_payload(metadata))
    metadata.signature = "invalid"
    with pytest.raises(RegistryError):
        registry.register(
            artifact_type="coverage_plan",
            metadata=metadata,
            impact=ChangeImpact.MAJOR,
            dependencies=metadata.upstream,
        )


def test_lineage_tracking(tmp_path: Path) -> None:
    config = RegistryConfig(artifact_prefixes={"coverage_plan": "cp"})
    signature_manager = SignatureManager(secret="secret")
    registry = GovernanceRegistry(config=config, signature_manager=signature_manager)

    parent_id = registry.assign_identifier("coverage_plan")
    parent_meta = _metadata(parent_id, "1.0.0")
    parent_meta.hash = compute_hash(manifest_payload(parent_meta))
    parent_meta.signature = signature_manager.sign(
        parent_meta.hash,
        context=(parent_meta.artifact_id, parent_meta.version),
    )
    registry.register(
        artifact_type="coverage_plan",
        metadata=parent_meta,
        impact=ChangeImpact.MAJOR,
        dependencies=parent_meta.upstream,
    )

    child_id = registry.assign_identifier("coverage_plan")
    child_meta = _metadata(child_id, "1.0.0")
    child_meta.hash = compute_hash(manifest_payload(child_meta))
    child_meta.signature = signature_manager.sign(
        child_meta.hash,
        context=(child_meta.artifact_id, child_meta.version),
    )
    dependency = ArtifactRef(
        artifact_id=parent_meta.artifact_id,
        version=parent_meta.version,
        hash=parent_meta.hash,
    )
    registry.register(
        artifact_type="coverage_plan",
        metadata=child_meta,
        impact=ChangeImpact.MAJOR,
        dependencies=(dependency,),
    )

    assert registry.parents(child_meta.artifact_id) == [parent_meta.artifact_id]
    assert registry.dependents(parent_meta.artifact_id) == [child_meta.artifact_id]

    lineage_path = registry.persist_lineage(tmp_path / "lineage.json")
    assert lineage_path.exists()
    payload = lineage_path.read_text()
    assert parent_meta.artifact_id in payload
    assert child_meta.artifact_id in payload

