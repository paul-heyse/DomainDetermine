"""State management utilities for the DomainDetermine CLI."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class SnapshotState:
    """State persisted between CLI runs."""

    context: str
    artifact_root: Path
    last_snapshot_id: Optional[str] = None


class StateStore:
    """Simple JSON-backed state store."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Optional[SnapshotState]:
        if not self._path.exists():
            return None
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return SnapshotState(
            context=data["context"],
            artifact_root=Path(data["artifact_root"]),
            last_snapshot_id=data.get("last_snapshot_id"),
        )

    def save(self, state: SnapshotState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload: Dict[str, str] = {
            "context": state.context,
            "artifact_root": str(state.artifact_root),
        }
        if state.last_snapshot_id:
            payload["last_snapshot_id"] = state.last_snapshot_id
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


