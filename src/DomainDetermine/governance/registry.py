"""Governance registry core orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Optional, Sequence

from DomainDetermine.governance.event_log import (
    GovernanceEvent,
    GovernanceEventLog,
    GovernanceEventType,
)
from DomainDetermine.governance.models import ArtifactMetadata, ArtifactRef
from DomainDetermine.governance.telemetry import GovernanceTelemetry
from DomainDetermine.governance.versioning import (
    ChangeImpact,
    SemanticVersioner,
    SignatureManager,
    compute_hash,
    manifest_payload,
)
from DomainDetermine.prompt_pack.registry import (
    PromptRegistry,
    PromptRegistryError,
    parse_prompt_reference,
)


class RegistryError(RuntimeError):
    """Raised when registry operations fail validation."""


@dataclass
class RegistryConfig:
    """Static configuration for registry namespaces."""

    artifact_prefixes: Mapping[str, str]

    def new_identifier(self, artifact_type: str, *, sequence: int) -> str:
        prefix = self.artifact_prefixes.get(artifact_type)
        if not prefix:
            raise RegistryError(f"Unknown artifact type '{artifact_type}'")
        return f"{prefix}-{sequence:06d}"


@dataclass
class GovernanceRegistry:
    """Stores artifact manifests and enforces publish policy."""

    config: RegistryConfig
    versioner: SemanticVersioner = field(default_factory=SemanticVersioner)
    signature_manager: Optional[SignatureManager] = None
    event_log: Optional[GovernanceEventLog] = None
    telemetry: Optional[GovernanceTelemetry] = None
    prompt_registry: Optional[PromptRegistry] = None

    def __post_init__(self) -> None:
        self._artifacts: MutableMapping[str, ArtifactMetadata] = {}
        self._sequences: MutableMapping[str, int] = {}
        self._parents: MutableMapping[str, set[str]] = {}
        self._children: MutableMapping[str, set[str]] = {}
        self._lineage_path: Optional[Path] = None

    # ------------------------------------------------------------------ CRUD
    def register(
        self,
        *,
        artifact_type: str,
        metadata: ArtifactMetadata,
        impact: ChangeImpact,
        dependencies: Sequence[ArtifactRef] = (),
        actor: Optional[str] = None,
        proposed_at: Optional[datetime] = None,
    ) -> ArtifactMetadata:
        """Register an artifact manifest after validation."""

        self._validate_dependencies(dependencies)
        self._validate_prompt_templates(metadata.prompt_templates)
        canonical = manifest_payload(metadata)
        computed_hash = compute_hash(canonical)
        if computed_hash != metadata.hash:
            raise RegistryError("manifest hash mismatch")
        if self.signature_manager:
            if not metadata.signature:
                raise RegistryError("signature required")
            if not self.signature_manager.verify(
                metadata.hash,
                metadata.signature,
                context=(metadata.artifact_id, metadata.version),
            ):
                raise RegistryError("invalid signature")
        previous = self._artifacts.get(metadata.artifact_id)
        expected_version = self.versioner.next_version(previous.version if previous else None, impact)
        if metadata.version != expected_version:
            raise RegistryError(
                "semantic version mismatch",
            )
        self._artifacts[metadata.artifact_id] = metadata
        parent_ids = {ref.artifact_id for ref in dependencies}
        self._parents[metadata.artifact_id] = parent_ids
        for parent_id in parent_ids:
            self._children.setdefault(parent_id, set()).add(metadata.artifact_id)
        self._children.setdefault(metadata.artifact_id, set())
        self._append_event(
            GovernanceEventType.PUBLISH_COMPLETED,
            metadata,
            actor=actor or metadata.created_by,
            payload={
                "artifact_type": artifact_type,
                "hash": metadata.hash,
                "impact": impact.value,
                "version": metadata.version,
                "dependencies": sorted(parent_ids),
            },
        )
        if self.telemetry:
            self.telemetry.record_publish(
                proposed_at=proposed_at or metadata.created_at,
                published_at=datetime.now(timezone.utc),
            )
        return metadata

    def assign_identifier(self, artifact_type: str) -> str:
        """Generate a new unique identifier for an artifact type."""

        sequence = self._sequences.get(artifact_type, 0) + 1
        self._sequences[artifact_type] = sequence
        return self.config.new_identifier(artifact_type, sequence=sequence)

    def get(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        return self._artifacts.get(artifact_id)

    def list_by_type(self, artifact_type: str) -> Iterable[ArtifactMetadata]:
        return (
            manifest
            for manifest in self._artifacts.values()
            if manifest.artifact_type == artifact_type
        )

    # ----------------------------------------------------------------- checks
    def _validate_dependencies(self, dependencies: Sequence[ArtifactRef]) -> None:
        for dependency in dependencies:
            manifest = self._artifacts.get(dependency.artifact_id)
            if manifest is None:
                raise RegistryError(f"missing dependency {dependency.artifact_id}")
            if manifest.hash != dependency.hash:
                raise RegistryError(
                    f"dependency hash mismatch for {dependency.artifact_id}",
                )

    # ------------------------------------------------------------- lineage ----
    def lineage_edges(self) -> Iterable[tuple[str, str]]:
        for parent, children in self._children.items():
            for child in children:
                yield (parent, child)

    def lineage_snapshot(self) -> Mapping[str, object]:
        return {
            "nodes": sorted(self._artifacts.keys()),
            "edges": [
                {"parent": parent, "child": child} for parent, child in self.lineage_edges()
            ],
        }

    def persist_lineage(self, path: Path) -> Path:
        snapshot = self.lineage_snapshot()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshot, indent=2, sort_keys=True))
        self._lineage_path = path
        return path

    def dependents(self, artifact_id: str) -> Sequence[str]:
        return sorted(self._children.get(artifact_id, set()))

    def parents(self, artifact_id: str) -> Sequence[str]:
        return sorted(self._parents.get(artifact_id, set()))

    # ----------------------------------------------------------- event hooks ---
    def attach_event_log(self, event_log: GovernanceEventLog) -> None:
        self.event_log = event_log

    def attach_prompt_registry(self, prompt_registry: PromptRegistry) -> None:
        """Attach a prompt registry for manifest reference validation."""

        self.prompt_registry = prompt_registry

    def attach_telemetry(self, telemetry: GovernanceTelemetry) -> None:
        self.telemetry = telemetry

    def _append_event(
        self,
        event_type: GovernanceEventType,
        metadata: ArtifactMetadata,
        *,
        payload: Mapping[str, object],
        actor: Optional[str] = None,
    ) -> None:
        if self.event_log is None:
            return
        artifact = ArtifactRef(
            artifact_id=metadata.artifact_id,
            version=metadata.version,
            hash=metadata.hash,
        )
        actor_name = actor or metadata.created_by
        event = GovernanceEvent(
            event_type=event_type,
            artifact=artifact,
            actor=actor_name,
            payload=payload,
        )
        self.event_log.append(event)
        if self.telemetry:
            self.telemetry.record_registry_notification(
                event_type=event_type,
                artifact=artifact,
                actor=actor_name,
                payload=payload,
            )

    def _validate_prompt_templates(self, references: Sequence[str]) -> None:
        if not references:
            return
        if self.prompt_registry is None:
            raise RegistryError("prompt registry required to validate prompt templates")
        for reference in references:
            try:
                template_id, version, expected_hash = parse_prompt_reference(reference)
            except PromptRegistryError as exc:
                raise RegistryError(str(exc)) from exc
            manifest = self.prompt_registry.resolve(template_id, version)
            if manifest is None:
                raise RegistryError(f"prompt {template_id}:{version} is not registered")
            if manifest.hash != expected_hash:
                raise RegistryError(
                    f"prompt hash mismatch for {template_id}:{version}",
                )


__all__ = [
    "ChangeImpact",
    "GovernanceRegistry",
    "RegistryConfig",
    "RegistryError",
]
