"""Backup and disaster recovery coordination."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence


@dataclass(frozen=True)
class BackupManifest:
    """Represents a single backup execution."""

    backup_id: str
    snapshot_time: datetime
    artifacts: Sequence[str]
    verification_hash: str
    replication_targets: Sequence[str]
    llm_artifacts: Sequence[Mapping[str, object]] = field(default_factory=tuple)

    def to_dict(self) -> Mapping[str, object]:
        return {
            "backup_id": self.backup_id,
            "snapshot_time": self.snapshot_time.isoformat(),
            "artifacts": list(self.artifacts),
            "verification_hash": self.verification_hash,
            "replication_targets": list(self.replication_targets),
            "llm_artifacts": [dict(artifact) for artifact in self.llm_artifacts],
        }


@dataclass
class BackupCoordinator:
    """Coordinates registry backups, replication, and integrity checks."""

    backup_root: Path
    schedule: Sequence[str] = field(default_factory=lambda: ("daily", "weekly"))

    def __post_init__(self) -> None:
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self._history: MutableMapping[str, BackupManifest] = {}

    def record_backup(
        self,
        *,
        backup_id: str,
        artifacts: Sequence[str],
        replication_targets: Sequence[str],
        verification_hash: str,
    ) -> BackupManifest:
        manifest = BackupManifest(
            backup_id=backup_id,
            snapshot_time=datetime.now(timezone.utc),
            artifacts=tuple(artifacts),
            verification_hash=verification_hash,
            replication_targets=tuple(replication_targets),
        )
        path = self.backup_root / f"{backup_id}.json"
        path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
        self._history[backup_id] = manifest
        return manifest

    def last_backup(self) -> BackupManifest | None:
        if not self._history:
            return None
        return max(self._history.values(), key=lambda manifest: manifest.snapshot_time)

    def integrity_report(self) -> Mapping[str, object]:
        manifests = list(self._history.values())
        return {
            "count": len(manifests),
            "latest": manifests[-1].to_dict() if manifests else None,
            "schedule": list(self.schedule),
        }


__all__ = ["BackupCoordinator", "BackupManifest"]
