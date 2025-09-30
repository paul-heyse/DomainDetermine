"""Utilities for generating and registering release readiness manifests."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

import yaml

from DomainDetermine.governance.models import ArtifactMetadata, ArtifactRef
from DomainDetermine.governance.registry import GovernanceRegistry
from DomainDetermine.governance.versioning import ChangeImpact, compute_hash, manifest_payload
from DomainDetermine.prompt_pack.registry import PromptRegistryError, parse_prompt_reference


@dataclass(frozen=True)
class ReleaseArtifact:
    """Represents an artifact deployed as part of a release."""

    name: str
    version: str
    hash: str


@dataclass(frozen=True)
class ApprovalRecord:
    """Approval metadata for a release."""

    role: str
    actor: str
    timestamp: str


@dataclass(frozen=True)
class ReleaseManifest:
    """Canonical release manifest used for governance."""

    release: str
    generated_at: datetime
    artifacts: tuple[ReleaseArtifact, ...]
    scorecard_path: str
    readiness_run_id: str
    feature_flags: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    secrets: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    migrations: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    approvals: tuple[ApprovalRecord, ...] = field(default_factory=tuple)
    rollback_plan: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Mapping[str, Any]:
        """Return a JSON-serialisable payload for the manifest."""

        def _dataclass_iter(items: Iterable[Any]) -> list[Any]:
            return [asdict(item) for item in items]

        payload: MutableMapping[str, Any] = {
            "release": self.release,
            "generated_at": self.generated_at.isoformat(),
            "artifacts": _dataclass_iter(self.artifacts),
            "scorecard_path": self.scorecard_path,
            "readiness_run_id": self.readiness_run_id,
            "feature_flags": [dict(flag) for flag in self.feature_flags],
            "secrets": [dict(secret) for secret in self.secrets],
            "migrations": [dict(migration) for migration in self.migrations],
            "approvals": _dataclass_iter(self.approvals),
            "rollback_plan": dict(self.rollback_plan),
            "metadata": dict(self.metadata),
        }
        return payload


def generate_release_manifest(
    *,
    release: str,
    artifacts: Sequence[Mapping[str, str]],
    scorecard_path: str,
    readiness_run_id: str,
    feature_flags: Sequence[Mapping[str, Any]] | None = None,
    secrets: Sequence[Mapping[str, Any]] | None = None,
    migrations: Sequence[Mapping[str, Any]] | None = None,
    approvals: Sequence[Mapping[str, str]] | None = None,
    rollback_plan: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ReleaseManifest:
    """Assemble a release manifest from the provided components."""

    artifact_records = tuple(ReleaseArtifact(**artifact) for artifact in artifacts)
    approval_records = tuple(ApprovalRecord(**approval) for approval in approvals or [])
    manifest = ReleaseManifest(
        release=release,
        generated_at=datetime.now(timezone.utc),
        artifacts=artifact_records,
        scorecard_path=scorecard_path,
        readiness_run_id=readiness_run_id,
        feature_flags=tuple(feature_flags or ()),
        secrets=tuple(secrets or ()),
        migrations=tuple(migrations or ()),
        approvals=approval_records,
        rollback_plan=rollback_plan or {},
        metadata=metadata or {},
    )
    return manifest


def write_manifest(manifest: ReleaseManifest, path: Path) -> Path:
    """Persist the manifest to disk in canonical JSON form."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest.to_dict()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def register_manifest(
    manifest: ReleaseManifest,
    registry: GovernanceRegistry,
    *,
    artifact_type: str,
    change_impact: ChangeImpact,
    tenant_id: str,
    license_tag: str,
    policy_pack_hash: str,
    change_reason: str,
    created_by: str,
    title: str | None = None,
    summary: str | None = None,
    dependencies: Sequence[ArtifactRef] = (),
    reviewers: Sequence[str] = (),
    waivers: Sequence[str] = (),
    environment_fingerprint: Mapping[str, str] | None = None,
    prompt_templates: Sequence[str] = (),
    artifact_id: str | None = None,
) -> ArtifactMetadata:
    """Register the manifest with the governance registry and return metadata."""

    manifest_dict = manifest.to_dict()
    manifest_hash = compute_hash(manifest_dict)
    if artifact_id is None:
        artifact_id = registry.assign_identifier(artifact_type)
        previous_version = None
    else:
        previous = registry.get(artifact_id)
        previous_version = previous.version if previous else None
    version = registry.versioner.next_version(previous_version, change_impact)
    fingerprint = dict(environment_fingerprint or {})
    fingerprint.setdefault("manifest_hash", manifest_hash)
    prompt_refs = tuple(prompt_templates)
    for reference in prompt_refs:
        try:
            parse_prompt_reference(reference)
        except PromptRegistryError as exc:
            raise ValueError(f"invalid prompt reference '{reference}': {exc}") from exc

    metadata = ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        version=version,
        hash="",
        signature="",
        title=title or f"Release {manifest.release}",
        summary=summary or f"Readiness manifest for release {manifest.release}",
        tenant_id=tenant_id,
        license_tag=license_tag,
        policy_pack_hash=policy_pack_hash,
        change_reason=change_reason,
        created_by=created_by,
        upstream=tuple(dependencies),
        reviewers=tuple(reviewers),
        approvals=tuple(record.actor for record in manifest.approvals),
        waivers=tuple(waivers),
        environment_fingerprint=fingerprint,
        prompt_templates=prompt_refs,
    )
    metadata_hash = compute_hash(manifest_payload(metadata))
    metadata.hash = metadata_hash
    if registry.signature_manager:
        metadata.signature = registry.signature_manager.sign(
            metadata_hash, context=(artifact_id, version)
        )
    registry.register(
        artifact_type=artifact_type,
        metadata=metadata,
        impact=change_impact,
        dependencies=dependencies,
    )
    return metadata


def _load_structure(path: Path) -> Mapping[str, Any]:
    if path.suffix in {".yml", ".yaml"}:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    return json.loads(path.read_text(encoding="utf-8"))


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        if value.startswith("{{") and value.endswith("}}"):  # simple token replacement
            key = value.strip("{}")
            return os.environ.get(key, "")
        return value
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    return value


def _load_release_config(path: Path) -> Mapping[str, Any]:
    raw = _load_structure(path)
    return _expand_env(raw)


def _load_readiness_report(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser(description="Generate release manifest for readiness")
    parser.add_argument("--config", required=True, help="YAML/JSON manifest template")
    parser.add_argument(
        "--report",
        default="readiness_report.json",
        help="Path to readiness report JSON generated by the pipeline",
    )
    parser.add_argument(
        "--output",
        default="release-manifest.json",
        help="Destination file for the generated manifest",
    )
    args = parser.parse_args()

    config = _load_release_config(Path(args.config))
    report = _load_readiness_report(Path(args.report))
    manifest = generate_release_manifest(
        release=config["release"],
        artifacts=config.get("artifacts", []),
        scorecard_path=report.get("scorecard", config.get("scorecard_path", "")),
        readiness_run_id=report.get("run_id", config.get("readiness_run_id", "")),
        feature_flags=config.get("feature_flags"),
        secrets=config.get("secrets"),
        migrations=config.get("migrations"),
        approvals=config.get("approvals"),
        rollback_plan=config.get("rollback_plan"),
        metadata=config.get("metadata"),
    )
    write_manifest(manifest, Path(args.output))
    print(json.dumps(manifest.to_dict(), indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
