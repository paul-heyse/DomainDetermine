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


__all__ = [
    "GovernanceEvent",
    "GovernanceEventLog",
    "GovernanceEventType",
]
