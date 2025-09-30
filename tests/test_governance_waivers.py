"""Tests for waiver governance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from DomainDetermine.governance.waivers import WaiverRecord, WaiverRegistry


def test_waiver_registry_stores_and_validates() -> None:
    registry = WaiverRegistry()
    active_waiver = WaiverRecord(
        waiver_id="waiver-1",
        owner="alice",
        justification="Test",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        advisories=("fairness",),
        mitigation_plan="Follow up",
    )
    registry.add(active_waiver)

    assert registry.get("waiver-1") == active_waiver
    validation = registry.validate(["waiver-1", "missing"])
    assert validation["waiver-1"] is True
    assert validation["missing"] is False


def test_expired_waiver_is_not_returned() -> None:
    registry = WaiverRegistry()
    expired = WaiverRecord(
        waiver_id="waiver-2",
        owner="bob",
        justification="Expired",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        advisories=(),
        mitigation_plan="",
    )
    registry.add(expired)
    assert registry.get("waiver-2") is None
    assert registry.validate(["waiver-2"]) == {"waiver-2": False}

