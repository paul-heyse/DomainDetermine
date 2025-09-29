"""Governance notification helpers for coverage auditor."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


@dataclass(slots=True)
class GovernanceNotifier:
    """Append-only governance registry writer."""

    registry_path: Path

    def __post_init__(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def notify(self, payload: Mapping[str, object]) -> None:
        enriched = dict(payload)
        enriched.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
        with self.registry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(enriched, sort_keys=True))
            handle.write("\n")


__all__ = ["GovernanceNotifier"]
