"""Core governance data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Mapping, Sequence

from pydantic import BaseModel, Field, field_validator


class Role(str, Enum):
    """Governance roles."""

    CREATOR = "creator"
    REVIEWER = "reviewer"
    APPROVER = "approver"
    AUDITOR = "auditor"
    READER = "reader"


@dataclass(frozen=True)
class TenantPolicy:
    """Tenancy isolation policy metadata."""

    tenant_id: str
    shared_with: Sequence[str] = field(default_factory=tuple)

    def allows(self, requester_tenant: str) -> bool:
        if requester_tenant == self.tenant_id:
            return True
        return requester_tenant in self.shared_with


class ArtifactRef(BaseModel):
    """Reference to a governed artifact."""

    artifact_id: str
    version: str
    hash: str


class ArtifactMetadata(BaseModel):
    """Manifest metadata persisted in the governance registry."""

    artifact_id: str
    artifact_type: str
    version: str
    hash: str
    signature: str
    title: str
    summary: str
    tenant_id: str
    license_tag: str
    policy_pack_hash: str
    change_reason: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    upstream: Sequence[ArtifactRef] = Field(default_factory=tuple)
    reviewers: Sequence[str] = Field(default_factory=tuple)
    approvals: Sequence[str] = Field(default_factory=tuple)
    waivers: Sequence[str] = Field(default_factory=tuple)
    environment_fingerprint: Mapping[str, str] = Field(default_factory=dict)
    prompt_templates: Sequence[str] = Field(default_factory=tuple)

    @field_validator("version")
    @classmethod
    def version_not_empty(cls, value: str) -> str:
        if not value:
            msg = "artifact version must be provided"
            raise ValueError(msg)
        return value

    def to_dict(self) -> Mapping[str, object]:  # pragma: no cover - convenience
        payload = self.model_dump()
        payload["created_at"] = self.created_at.isoformat()
        payload["upstream"] = [ref.model_dump() for ref in self.upstream]
        payload["reviewers"] = list(self.reviewers)
        payload["approvals"] = list(self.approvals)
        payload["waivers"] = list(self.waivers)
        payload["environment_fingerprint"] = dict(self.environment_fingerprint)
        return payload


@dataclass(frozen=True)
class LLMArtifact:
    """Summarizes LLM engine and serving artifacts for governance logging."""

    engine_hash: str
    engine_version: str
    tokenizer_hash: str
    schema_registry_path: Path
    config_path: Path

    def to_payload(self) -> Mapping[str, object]:
        return {
            "engine_hash": self.engine_hash,
            "engine_version": self.engine_version,
            "tokenizer_hash": self.tokenizer_hash,
            "schema_registry_path": str(self.schema_registry_path),
            "config_path": str(self.config_path),
        }


__all__ = [
    "ArtifactMetadata",
    "ArtifactRef",
    "LLMArtifact",
    "Role",
    "TenantPolicy",
]
