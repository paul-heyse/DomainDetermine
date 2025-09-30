"""Command-line tool for evaluating readiness release gates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from DomainDetermine.readiness.manifest import ApprovalRecord, ReleaseManifest
from DomainDetermine.readiness.rehearsal import record_rehearsal_check


class GateError(RuntimeError):
    """Raised when gate validation fails."""


def _load_manifest(path: Path) -> ReleaseManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    approvals = tuple(
        ApprovalRecord(
            role=item.get("role", ""),
            actor=item.get("actor", ""),
            timestamp=item.get("timestamp", ""),
        )
        for item in payload.get("approvals", [])
    )
    artifacts = tuple(payload.get("artifacts", []))
    manifest = ReleaseManifest(
        release=payload["release"],
        generated_at=datetime.fromisoformat(payload["generated_at"]),
        artifacts=tuple(
            dict(name=artifact["name"], version=artifact["version"], hash=artifact["hash"])
            for artifact in artifacts
        ),
        scorecard_path=payload.get("scorecard_path", ""),
        readiness_run_id=payload.get("readiness_run_id", ""),
        feature_flags=tuple(payload.get("feature_flags", [])),
        secrets=tuple(payload.get("secrets", [])),
        migrations=tuple(payload.get("migrations", [])),
        approvals=approvals,
        rollback_plan=payload.get("rollback_plan", {}),
        metadata=payload.get("metadata", {}),
    )
    return manifest


def _load_gate_config(path: Path) -> Mapping[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _required_roles(config: Mapping[str, Any]) -> Sequence[str]:  # pragma: no cover - trivial
    roles = config.get("required_roles", [])
    return tuple(str(role) for role in roles)


def _extract_approvals(manifest: ReleaseManifest) -> Mapping[str, str]:
    approvals = {}
    for approval in manifest.approvals:
        approvals[approval.role] = approval.actor
    return approvals


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def evaluate_gate(
    manifest_path: Path,
    *,
    config_path: Path,
    release_id: str | None = None,
) -> None:
    manifest = _load_manifest(manifest_path)
    config = _load_gate_config(config_path)
    approvals_map = _extract_approvals(manifest)
    required_roles = _required_roles(config)
    missing_roles = [role for role in required_roles if role not in approvals_map]
    if missing_roles and config.get("enforce_approvals", True):
        raise GateError(
            f"Missing required approvals for roles: {', '.join(sorted(missing_roles))}"
        )

    # Evaluate rollback rehearsal freshness
    plan = manifest.rollback_plan or {}
    rehearsed_at = _parse_datetime(plan.get("rehearsed_at"))
    if config.get("require_rehearsal", True):
        if rehearsed_at is None:
            raise GateError("Rollback rehearsal timestamp missing")
        max_age = int(config.get("max_rehearsal_age_days", 30))
        age = datetime.now(timezone.utc) - rehearsed_at
        stale = age.days > max_age
        record_rehearsal_check(
            rehearsed_at=rehearsed_at,
            max_age_days=max_age,
            stale=stale,
            release_id=release_id or manifest.release,
        )
        if stale:
            raise GateError(
                f"Rollback rehearsal older than {max_age} days (age {age.days} days)"
            )

    disallow_waivers = config.get("disallow_waivers", False)
    if disallow_waivers and manifest.metadata.get("waivers"):
        raise GateError("Waivers present but disallowed for this release environment")


def main() -> None:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser(description="Evaluate readiness deployment gate")
    parser.add_argument("--manifest", required=True, help="Path to release manifest JSON")
    parser.add_argument("--config", required=True, help="Gate configuration YAML")
    parser.add_argument(
        "--release-id",
        default=None,
        help="Optional release identifier for telemetry events",
    )
    args = parser.parse_args()

    evaluate_gate(
        Path(args.manifest),
        config_path=Path(args.config),
        release_id=args.release_id,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
