"""Prompt pack semantic version tooling and governance integration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence

from DomainDetermine.governance.event_log import (
    GovernanceEventLog,
    log_prompt_published,
    log_prompt_rolled_back,
    log_prompt_waiver_granted,
)
from DomainDetermine.governance.models import ArtifactRef
from DomainDetermine.governance.versioning import ChangeImpact, SemanticVersioner, compute_hash
from DomainDetermine.prompt_pack.loader import PromptTemplateLoader, TemplateRecord
from DomainDetermine.prompt_pack.registry import (
    PromptManifest,
    PromptRegistry,
    PromptRegistryError,
    format_prompt_reference,
)


@dataclass(frozen=True)
class PromptReleaseRecord:
    """Structured payload describing a prompt release."""

    template_id: str
    version: str
    schema_id: str
    policy_id: str
    impact: ChangeImpact
    hash: str
    rationale: str
    owners: Sequence[str]
    expected_metrics: Mapping[str, object]
    approvals: Sequence[str]
    related_manifests: Sequence[str]
    timestamp: datetime

    def to_mapping(self) -> Mapping[str, object]:
        payload: MutableMapping[str, object] = {
            "template_id": self.template_id,
            "version": self.version,
            "schema_id": self.schema_id,
            "policy_id": self.policy_id,
            "impact": self.impact.value,
            "hash": self.hash,
            "rationale": self.rationale,
            "owners": list(self.owners),
            "expected_metrics": dict(self.expected_metrics),
            "approvals": list(self.approvals),
            "related_manifests": list(self.related_manifests),
            "timestamp": self.timestamp.isoformat(),
        }
        return payload


class PromptVersionManager:
    """Coordinates semantic version validation and governance logging."""

    def __init__(
        self,
        root: Path,
        registry: PromptRegistry,
        *,
        changelog_path: Path | None = None,
        journal_path: Path | None = None,
        event_log: GovernanceEventLog | None = None,
    ) -> None:
        self._root = root
        self._loader = PromptTemplateLoader(root)
        self._registry = registry
        self._versioner = SemanticVersioner()
        self._changelog_path = changelog_path
        self._journal_path = journal_path
        self._event_log = event_log

    # ------------------------------------------------------------------ publish
    def publish(
        self,
        template_id: str,
        *,
        impact: ChangeImpact,
        rationale: str,
        owners: Sequence[str],
        expected_metrics: Mapping[str, object] | None = None,
        approvals: Sequence[str] | None = None,
        actor: str = "prompt-governance",
        related_manifests: Sequence[str] | None = None,
    ) -> PromptManifest:
        """Validate, register, and log a prompt template release."""

        record = self._load_record(template_id)
        metadata = record.load_metadata()
        declared_version = metadata.get("version")
        if not declared_version:
            msg = f"Template metadata for {template_id} is missing a version"
            raise PromptRegistryError(msg)
        previous_version = self._registry.latest_version(template_id)
        expected_version = self._versioner.next_version(previous_version, impact)
        if declared_version != expected_version:
            msg = (
                f"Declared version {declared_version} for {template_id} does not match"
                f" expected semantic bump {expected_version} for impact '{impact.value}'"
            )
            raise PromptRegistryError(msg)
        schema_id = metadata.get("schema")
        policy_id = metadata.get("policy")
        if not (schema_id and policy_id):
            msg = f"Template metadata for {template_id} must include schema and policy identifiers"
            raise PromptRegistryError(msg)
        prompt_hash = compute_prompt_hash(record)
        manifest = PromptManifest(
            template_id=template_id,
            version=declared_version,
            schema_id=schema_id,
            policy_id=policy_id,
            hash=prompt_hash,
        )
        self._registry.register(manifest)
        release_record = PromptReleaseRecord(
            template_id=template_id,
            version=declared_version,
            schema_id=schema_id,
            policy_id=policy_id,
            impact=impact,
            hash=prompt_hash,
            rationale=rationale,
            owners=tuple(owners),
            expected_metrics=dict(expected_metrics or {}),
            approvals=tuple(approvals or ()),
            related_manifests=tuple(related_manifests or ()),
            timestamp=datetime.now(timezone.utc),
        )
        self._log_release(release_record)
        self._emit_publish_event(release_record, actor=actor)
        return manifest

    # ----------------------------------------------------------------- rollback
    def record_rollback(
        self,
        template_id: str,
        version: str,
        *,
        actor: str,
        reason: str,
        waiver_id: str | None = None,
    ) -> None:
        """Emit a governance rollback event for a prompt version."""

        manifest = self._registry.resolve(template_id, version)
        if manifest is None:
            raise PromptRegistryError(
                f"Cannot log rollback for unregistered prompt {template_id}:{version}",
            )
        payload = {
            "reason": reason,
        }
        if waiver_id:
            payload["waiver_id"] = waiver_id
        self._emit_rollback_event(manifest, actor=actor, payload=payload)

    def record_waiver(
        self,
        template_id: str,
        version: str,
        *,
        actor: str,
        justification: str,
        expiry: str,
    ) -> None:
        """Emit a governance waiver approval event for a prompt version."""

        manifest = self._registry.resolve(template_id, version)
        if manifest is None:
            raise PromptRegistryError(
                f"Cannot log waiver for unregistered prompt {template_id}:{version}",
            )
        payload = {
            "justification": justification,
            "expiry": expiry,
        }
        self._emit_waiver_event(manifest, actor=actor, payload=payload)

    # ---------------------------------------------------------------- utilities
    def reference(self, manifest: PromptManifest) -> str:
        """Return canonical reference for a registered manifest."""

        return format_prompt_reference(manifest)

    def _load_record(self, template_id: str) -> TemplateRecord:
        records = {record.load_metadata().get("template_id"): record for record in self._loader.discover()}
        if template_id not in records:
            msg = f"Prompt template '{template_id}' not found in prompt pack root {self._root}"
            raise PromptRegistryError(msg)
        return records[template_id]

    def _log_release(self, record: PromptReleaseRecord) -> None:
        if self._changelog_path:
            self._append_changelog(record)
        if self._journal_path:
            self._append_journal(record)

    def _append_changelog(self, record: PromptReleaseRecord) -> None:
        header = f"## {record.template_id} {record.version} - {record.timestamp.date().isoformat()}\n"
        lines = [header]
        lines.append(f"- Impact: {record.impact.value}\n")
        if record.owners:
            lines.append(f"- Owners: {', '.join(record.owners)}\n")
        else:
            lines.append("- Owners: n/a\n")
        lines.append(f"- Rationale: {record.rationale}\n")
        if record.expected_metrics:
            lines.append("- Expected metrics:\n")
            for name, value in sorted(record.expected_metrics.items()):
                lines.append(f"  - {name}: {value}\n")
        lines.append(f"- Hash: {record.hash}\n")
        if record.approvals:
            lines.append(f"- Approvals: {', '.join(record.approvals)}\n")
        if record.related_manifests:
            lines.append(f"- Related manifests: {', '.join(record.related_manifests)}\n")
        lines.append("\n")
        path = self._changelog_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("# Prompt Pack Changelog\n\n", encoding="utf-8")
        with path.open("a", encoding="utf-8") as handle:
            handle.writelines(lines)

    def _append_journal(self, record: PromptReleaseRecord) -> None:
        path = self._journal_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_mapping(), sort_keys=True))
            handle.write("\n")

    def _emit_publish_event(self, record: PromptReleaseRecord, *, actor: str) -> None:
        if self._event_log is None:
            return
        artifact = ArtifactRef(
            artifact_id=record.template_id,
            version=record.version,
            hash=record.hash,
        )
        payload: MutableMapping[str, object] = {
            "approvals": list(record.approvals),
            "owners": list(record.owners),
            "rationale": record.rationale,
            "expected_metrics": dict(record.expected_metrics),
            "related_manifests": list(record.related_manifests),
            "impact": record.impact.value,
        }
        log_prompt_published(
            self._event_log,
            artifact=artifact,
            actor=actor,
            payload=payload,
        )

    def _emit_rollback_event(
        self,
        manifest: PromptManifest,
        *,
        actor: str,
        payload: Mapping[str, object],
    ) -> None:
        if self._event_log is None:
            return
        artifact = ArtifactRef(
            artifact_id=manifest.template_id,
            version=manifest.version,
            hash=manifest.hash,
        )
        log_prompt_rolled_back(self._event_log, artifact=artifact, actor=actor, payload=payload)

    def _emit_waiver_event(
        self,
        manifest: PromptManifest,
        *,
        actor: str,
        payload: Mapping[str, object],
    ) -> None:
        if self._event_log is None:
            return
        artifact = ArtifactRef(
            artifact_id=manifest.template_id,
            version=manifest.version,
            hash=manifest.hash,
        )
        log_prompt_waiver_granted(
            self._event_log,
            artifact=artifact,
            actor=actor,
            payload=payload,
        )


def compute_prompt_hash(record: TemplateRecord) -> str:
    """Compute a deterministic hash over template assets."""

    schema_payload = json.loads(record.schema_path.read_text(encoding="utf-8"))
    policy_payload = json.loads(record.policy_path.read_text(encoding="utf-8"))
    payload = {
        "template": record.load_template(),
        "metadata": record.load_metadata(),
        "schema": schema_payload,
        "policy": policy_payload,
    }
    return compute_hash(payload)


__all__ = [
    "PromptReleaseRecord",
    "PromptVersionManager",
    "compute_prompt_hash",
]
