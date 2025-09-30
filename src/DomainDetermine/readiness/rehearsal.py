"""Rollback rehearsal telemetry helpers."""

from __future__ import annotations

from datetime import datetime

from DomainDetermine.governance.telemetry import GovernanceTelemetry


def record_rehearsal_check(
    *,
    rehearsed_at: datetime,
    max_age_days: int,
    stale: bool,
    release_id: str | None = None,
) -> None:
    """Emit governance telemetry for a rollback rehearsal evaluation."""

    telemetry = GovernanceTelemetry()
    telemetry.record_rehearsal(
        rehearsal_time=rehearsed_at,
        max_age_days=max_age_days,
        stale=stale,
        release_id=release_id,
    )


__all__ = ["record_rehearsal_check"]
