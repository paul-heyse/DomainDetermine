"""Data models for the coverage auditor capability."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Mapping, MutableMapping, Optional, Sequence


class GateLevel(str, Enum):
    """Classifies gate severity."""

    BLOCKING = "blocking"
    ADVISORY = "advisory"


class MetricStatus(str, Enum):
    """Represents the outcome of a metric evaluation."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    WAIVED = "waived"


@dataclass(slots=True)
class AuditRunConfig:
    """Configuration supplied to an audit run."""

    kos_snapshot_id: str
    plan_version: str
    audit_run_id: str
    signer_key_id: str
    policy_pack_version: str
    facet_domains: Mapping[str, Sequence[str]] = field(default_factory=dict)
    branch_column: str = "branch"
    quota_column: str = "planned_quota"
    locale_column: str = "locale"
    difficulty_column: str = "difficulty"


@dataclass(slots=True)
class PolicyPack:
    """Represents policy constraints enforced by the auditor."""

    forbidden_concepts: Sequence[str] = field(default_factory=tuple)
    jurisdiction_rules: Mapping[str, Sequence[str]] = field(default_factory=dict)
    licensing_restrictions: Mapping[str, Sequence[str]] = field(default_factory=dict)
    pii_required_flags: Sequence[str] = field(default_factory=tuple)
    branch_floors: Mapping[str, float] = field(default_factory=dict)
    branch_ceilings: Mapping[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class AuditMetric:
    """Single metric computed during auditing."""

    name: str
    value: float
    threshold: Optional[float]
    comparator: str
    status: MetricStatus
    gate_level: GateLevel
    rationale: str
    owner: str
    extra: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class AuditFinding:
    """Represents a per-stratum finding recorded in the audit dataset."""

    concept_id: str
    status: MetricStatus
    reasons: Sequence[str]
    gate_level: GateLevel


@dataclass(slots=True)
class AuditArtifactPaths:
    """Locations of generated audit artifacts."""

    dataset_uri: str
    certificate_uri: str
    report_uri: str
    assets: Sequence[str] = field(default_factory=tuple)


@dataclass(slots=True)
class AuditCertificate:
    """Machine-readable coverage certificate."""

    metadata: Mapping[str, str]
    metrics: Sequence[AuditMetric]
    findings_summary: Mapping[str, int]
    waivers: Sequence[Mapping[str, str]]
    signature: str


@dataclass(slots=True)
class AuditResult:
    """Aggregate result returned by the coverage auditor."""

    audit_dataset: Sequence[Mapping[str, object]]
    metrics: Sequence[AuditMetric]
    findings: Sequence[AuditFinding]
    certificate: AuditCertificate
    report: Mapping[str, object]
    artifact_paths: AuditArtifactPaths
    telemetry_events: Sequence[Mapping[str, object]]


def generate_signature(payload: Mapping[str, object], *, signer_key_id: str) -> str:
    """Return a deterministic signature for the payload."""

    hasher = hashlib.sha256()
    hasher.update(signer_key_id.encode())
    serialized = sorted(_flatten_payload(payload))
    for key, value in serialized:
        hasher.update(f"{key}={value}".encode())
    return hasher.hexdigest()


def _flatten_payload(payload: Mapping[str, object], prefix: str = "") -> Iterable[tuple[str, object]]:
    """Yield flattened key/value pairs for hashing."""

    for key, value in payload.items():
        composite_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, Mapping):
            yield from _flatten_payload(value, composite_key)
        elif isinstance(value, (list, tuple)):
            for idx, item in enumerate(value):
                list_key = f"{composite_key}[{idx}]"
                if isinstance(item, Mapping):
                    yield from _flatten_payload(item, list_key)
                else:
                    yield list_key, item
        else:
            yield composite_key, value


def default_metadata(config: AuditRunConfig) -> MutableMapping[str, str]:
    """Return metadata dictionary common to all artifacts."""

    return {
        "kos_snapshot_id": config.kos_snapshot_id,
        "plan_version": config.plan_version,
        "audit_run_id": config.audit_run_id,
        "policy_pack_version": config.policy_pack_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


__all__ = [
    "AuditArtifactPaths",
    "AuditCertificate",
    "AuditFinding",
    "AuditMetric",
    "AuditResult",
    "AuditRunConfig",
    "GateLevel",
    "MetricStatus",
    "PolicyPack",
    "default_metadata",
    "generate_signature",
]
