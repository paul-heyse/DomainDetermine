"""Helpers for emitting governance events and alerts from the service layer."""

from __future__ import annotations

import logging
from typing import Mapping, Optional

from DomainDetermine.governance.event_log import (
    GovernanceEventLog,
    GovernanceEventType,
    log_service_job_event,
)
from DomainDetermine.governance.models import ArtifactRef

LOGGER = logging.getLogger("DomainDetermine.service.jobs")


def _job_artifact(job_id: str, tenant: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=f"service-job:{tenant}:{job_id}",
        version="v1",
        hash=job_id,
    )


def emit_job_event(
    *,
    event_log: Optional[GovernanceEventLog],
    event_type: GovernanceEventType,
    job_id: str,
    tenant: str,
    actor: str,
    payload: Mapping[str, object],
) -> None:
    if event_log is None:
        return
    log_service_job_event(
        event_log,
        event_type=event_type,
        artifact=_job_artifact(job_id, tenant),
        actor=actor,
        payload=payload,
    )


def alert_quota_violation(job_id: str, tenant: str, quota_type: str, used: int, limit: int) -> None:
    LOGGER.warning(
        "Quota exceeded for service job",
        extra={
            "job_id": job_id,
            "tenant": tenant,
            "quota_type": quota_type,
            "used": used,
            "limit": limit,
        },
    )


__all__ = ["emit_job_event", "alert_quota_violation"]
