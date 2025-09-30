"""Append-only governance event log with signatures."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Optional, Sequence

from DomainDetermine.governance.models import ArtifactRef


class GovernanceEventType(str, Enum):
    """Enumerates audit-relevant governance events."""

    PROPOSAL_CREATED = "proposal_created"
    BUILD_ATTACHED = "build_attached"
    AUDIT_COMPLETED = "audit_completed"
    APPROVAL_RECORDED = "approval_recorded"
    WAIVER_GRANTED = "waiver_granted"
    PUBLISH_REQUESTED = "publish_requested"
    PUBLISH_COMPLETED = "publish_completed"
    ROLLBACK_INITIATED = "rollback_initiated"
    ROLLBACK_COMPLETED = "rollback_completed"
    PROMPT_PUBLISHED = "prompt_published"
    PROMPT_ROLLED_BACK = "prompt_rolled_back"
    PROMPT_QUALITY_ALERT = "prompt_quality_alert"
    LLM_ENGINE_PUBLISHED = "llm_engine_published"
    LLM_WARMUP_COMPLETED = "llm_warmup_completed"
    LLM_WARMUP_FAILED = "llm_warmup_failed"
    LLM_ROLLBACK_COMPLETED = "llm_rollback_completed"
    LLM_OBSERVABILITY_ALERT = "llm_observability_alert"
    SERVICE_JOB_ENQUEUED = "service_job_enqueued"
    SERVICE_JOB_COMPLETED = "service_job_completed"
    SERVICE_JOB_FAILED = "service_job_failed"
    SERVICE_JOB_QUOTA_EXCEEDED = "service_job_quota_exceeded"
    MAPPING_BATCH_PUBLISHED = "mapping_batch_published"
    MAPPING_REVIEW_REQUIRED = "mapping_review_required"


@dataclass(slots=True)
class GovernanceEvent:
    """Immutable event record stored in the log."""

    event_type: GovernanceEventType
    artifact: ArtifactRef
    actor: str
    payload: Mapping[str, object] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature: Optional[str] = None

    def to_dict(self) -> MutableMapping[str, object]:
        data: MutableMapping[str, object] = {
            "event_type": self.event_type.value,
            "artifact": self.artifact.__dict__,
            "actor": self.actor,
            "payload": dict(self.payload),
            "timestamp": self.timestamp.isoformat(),
        }
        if self.signature:
            data["signature"] = self.signature
        return data


class GovernanceEventLog:
    """Handles append-only event logging with deterministic signatures."""

    def __init__(self, path: Path, *, secret: Optional[str] = None) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._secret = secret or os.getenv("GOVERNANCE_EVENT_SECRET")
        if not self._secret:
            msg = (
                "Governance event log secret must be provided via constructor or GOV"
                "ERNANCE_EVENT_SECRET environment variable"
            )
            raise ValueError(msg)

    def append(self, event: GovernanceEvent) -> GovernanceEvent:
        signed_event = self._sign_event(event)
        serialized = json.dumps(signed_event.to_dict(), sort_keys=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.write("\n")
        return signed_event

    def query(self, *, artifact_id: Optional[str] = None, event_types: Optional[Sequence[GovernanceEventType]] = None) -> Iterable[GovernanceEvent]:
        if not self._path.exists():
            return []
        types = {etype.value for etype in event_types} if event_types else None
        results: list[GovernanceEvent] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if types and raw.get("event_type") not in types:
                    continue
                artifact = raw.get("artifact", {})
                if artifact_id and artifact.get("artifact_id") != artifact_id:
                    continue
                event = GovernanceEvent(
                    event_type=GovernanceEventType(raw["event_type"]),
                    artifact=ArtifactRef(
                        artifact_id=artifact["artifact_id"],
                        version=artifact["version"],
                        hash=artifact["hash"],
                    ),
                    actor=raw["actor"],
                    payload=raw.get("payload", {}),
                    timestamp=datetime.fromisoformat(raw["timestamp"]),
                    signature=raw.get("signature"),
                )
                results.append(event)
        return results

    def _sign_event(self, event: GovernanceEvent) -> GovernanceEvent:
        payload = event.to_dict()
        payload.pop("signature", None)
        canonical = json.dumps(payload, sort_keys=True)
        fingerprint = sha256()
        fingerprint.update(self._secret.encode("utf-8"))
        fingerprint.update(canonical.encode("utf-8"))
        signature = fingerprint.hexdigest()
        return GovernanceEvent(
            event_type=event.event_type,
            artifact=event.artifact,
            actor=event.actor,
            payload=event.payload,
            timestamp=event.timestamp,
            signature=signature,
        )


def log_llm_engine_published(log: GovernanceEventLog, artifact: ArtifactRef, actor: str, payload: Mapping[str, object]) -> GovernanceEvent:
    event = GovernanceEvent(
        event_type=GovernanceEventType.LLM_ENGINE_PUBLISHED,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


def log_llm_warmup_completed(log: GovernanceEventLog, artifact: ArtifactRef, actor: str, payload: Mapping[str, object]) -> GovernanceEvent:
    event = GovernanceEvent(
        event_type=GovernanceEventType.LLM_WARMUP_COMPLETED,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


def log_llm_warmup_failed(log: GovernanceEventLog, artifact: ArtifactRef, actor: str, payload: Mapping[str, object]) -> GovernanceEvent:
    event = GovernanceEvent(
        event_type=GovernanceEventType.LLM_WARMUP_FAILED,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


def log_llm_rollback_completed(log: GovernanceEventLog, artifact: ArtifactRef, actor: str, payload: Mapping[str, object]) -> GovernanceEvent:
    event = GovernanceEvent(
        event_type=GovernanceEventType.LLM_ROLLBACK_COMPLETED,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


def log_llm_observability_alert(log: GovernanceEventLog, artifact: ArtifactRef, actor: str, payload: Mapping[str, object]) -> GovernanceEvent:
    event = GovernanceEvent(
        event_type=GovernanceEventType.LLM_OBSERVABILITY_ALERT,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


def log_service_job_event(
    log: GovernanceEventLog,
    *,
    event_type: GovernanceEventType,
    artifact: ArtifactRef,
    actor: str,
    payload: Mapping[str, object],
) -> GovernanceEvent:
    if event_type not in {
        GovernanceEventType.SERVICE_JOB_ENQUEUED,
        GovernanceEventType.SERVICE_JOB_COMPLETED,
        GovernanceEventType.SERVICE_JOB_FAILED,
        GovernanceEventType.SERVICE_JOB_QUOTA_EXCEEDED,
    }:
        raise ValueError("Invalid service job event type")
    event = GovernanceEvent(
        event_type=event_type,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


def log_prompt_published(
    log: GovernanceEventLog,
    *,
    artifact: ArtifactRef,
    actor: str,
    payload: Mapping[str, object],
) -> GovernanceEvent:
    """Append a prompt published event."""

    event = GovernanceEvent(
        event_type=GovernanceEventType.PROMPT_PUBLISHED,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


def log_prompt_rolled_back(
    log: GovernanceEventLog,
    *,
    artifact: ArtifactRef,
    actor: str,
    payload: Mapping[str, object],
) -> GovernanceEvent:
    """Append a prompt rollback event."""

    event = GovernanceEvent(
        event_type=GovernanceEventType.PROMPT_ROLLED_BACK,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


def log_prompt_quality_alert(
    log: GovernanceEventLog,
    *,
    artifact: ArtifactRef,
    actor: str,
    payload: Mapping[str, object],
) -> GovernanceEvent:
    """Append a prompt quality alert event for KPI regressions."""

    event = GovernanceEvent(
        event_type=GovernanceEventType.PROMPT_QUALITY_ALERT,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


def log_prompt_waiver_granted(
    log: GovernanceEventLog,
    *,
    artifact: ArtifactRef,
    actor: str,
    payload: Mapping[str, object],
) -> GovernanceEvent:
    """Append a prompt waiver granted event."""

    event = GovernanceEvent(
        event_type=GovernanceEventType.WAIVER_GRANTED,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


def log_mapping_batch_published(
    log: GovernanceEventLog,
    *,
    artifact: ArtifactRef,
    actor: str,
    payload: Mapping[str, object],
) -> GovernanceEvent:
    event = GovernanceEvent(
        event_type=GovernanceEventType.MAPPING_BATCH_PUBLISHED,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


def log_mapping_review_required(
    log: GovernanceEventLog,
    *,
    artifact: ArtifactRef,
    actor: str,
    payload: Mapping[str, object],
) -> GovernanceEvent:
    event = GovernanceEvent(
        event_type=GovernanceEventType.MAPPING_REVIEW_REQUIRED,
        artifact=artifact,
        actor=actor,
        payload=payload,
    )
    return log.append(event)


__all__ = [
    "GovernanceEvent",
    "GovernanceEventLog",
    "GovernanceEventType",
    "log_prompt_published",
    "log_prompt_rolled_back",
    "log_prompt_quality_alert",
    "log_prompt_waiver_granted",
    "log_llm_engine_published",
    "log_llm_observability_alert",
    "log_llm_rollback_completed",
    "log_llm_warmup_completed",
    "log_llm_warmup_failed",
    "log_service_job_event",
    "log_mapping_batch_published",
    "log_mapping_review_required",
]
