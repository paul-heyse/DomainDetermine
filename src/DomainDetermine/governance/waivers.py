"""Waiver governance and lifecycle management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, MutableMapping, Optional, Sequence


@dataclass(frozen=True)
class WaiverRecord:
    """Represents an advisory waiver."""

    waiver_id: str
    owner: str
    justification: str
    expires_at: datetime
    advisories: Sequence[str]
    mitigation_plan: str

    @property
    def active(self) -> bool:
        return self.expires_at > datetime.now(timezone.utc)


class WaiverRegistry:
    """Stores waiver records and enforces expiry."""

    def __init__(self) -> None:
        self._records: MutableMapping[str, WaiverRecord] = {}

    def add(self, waiver: WaiverRecord) -> None:
        self._records[waiver.waiver_id] = waiver

    def get(self, waiver_id: str) -> Optional[WaiverRecord]:
        waiver = self._records.get(waiver_id)
        if waiver and not waiver.active:
            return None
        return waiver

    def validate(self, waiver_ids: Sequence[str]) -> Mapping[str, bool]:
        return {waiver_id: bool(self.get(waiver_id)) for waiver_id in waiver_ids}


__all__ = ["WaiverRecord", "WaiverRegistry"]

