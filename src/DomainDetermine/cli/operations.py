"""Utilities for executing CLI operations with idempotency semantics."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

import click

from .config import ResolvedConfig
from .logging import progress_spinner

JsonDict = Dict[str, Any]


@dataclass(frozen=True)
class CommandRuntime:
    """Holds context required during command execution."""

    config: ResolvedConfig
    logger: logging.Logger

    @property
    def dry_run(self) -> bool:
        return self.config.dry_run

    @property
    def artifact_root(self) -> Path:
        return self.config.artifact_root


class OperationOutcome:
    """Simple enum-like outcomes for operations."""

    EXECUTED = "executed"
    DRY_RUN = "dry-run"
    NOOP = "no-op"


class OperationExecutor:
    """Executes CLI operations while enforcing idempotency."""

    def __init__(self, runtime: CommandRuntime) -> None:
        self._runtime = runtime
        self._state_dir = runtime.artifact_root / ".cli_state"
        self._state_dir.mkdir(parents=True, exist_ok=True)

    def _manifest_path(self, verb: str) -> Path:
        return self._state_dir / f"{verb}.json"

    def _load_manifest(self, verb: str) -> JsonDict:
        path = self._manifest_path(verb)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._runtime.logger.warning(
                "Manifest corrupted; resetting",
                extra={"verb": verb, "path": str(path)},
            )
            return {}

    def _persist_manifest(self, verb: str, manifest: JsonDict) -> None:
        path = self._manifest_path(verb)
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _fingerprint(payload: Mapping[str, Any]) -> str:
        serialised = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialised.encode("utf-8")).hexdigest()

    def run(
        self,
        verb: str,
        subject: str,
        payload: Mapping[str, Any],
        performer: Callable[[], Optional[Path]],
        preview_message: str,
    ) -> str:
        """Run an operation with idempotency and progress reporting."""

        manifest = self._load_manifest(verb)
        entry = manifest.get(subject)
        fingerprint = self._fingerprint(payload)

        if entry and entry.get("fingerprint") == fingerprint:
            self._runtime.logger.info(
                "Operation skipped; fingerprint unchanged",
                extra={"verb": verb, "subject": subject, "fingerprint": fingerprint},
            )
            click.echo(f"[no-op] {verb} {subject} is already up to date")
            return OperationOutcome.NOOP

        if self._runtime.dry_run:
            self._runtime.logger.info(
                "Dry-run preview",
                extra={"verb": verb, "subject": subject, "payload": dict(payload)},
            )
            click.echo(f"[dry-run] {preview_message}")
            return OperationOutcome.DRY_RUN

        artifact_path: Optional[Path]
        if self._runtime.config.log_format == "json":
            artifact_path = performer()
        else:
            with progress_spinner(f"{verb.capitalize()} {subject}"):
                artifact_path = performer()

        manifest[subject] = {
            "fingerprint": fingerprint,
            "payload": dict(payload),
            "artifact": str(artifact_path) if artifact_path else None,
        }
        self._persist_manifest(verb, manifest)

        self._runtime.logger.info(
            "Operation executed",
            extra={
                "verb": verb,
                "subject": subject,
                "artifact": str(artifact_path) if artifact_path else None,
                "fingerprint": fingerprint,
            },
        )
        click.echo(f"[ok] {verb} {subject}")
        if artifact_path:
            click.echo(f"       artifact: {artifact_path}")
        return OperationOutcome.EXECUTED


def build_runtime(ctx: click.Context) -> CommandRuntime:
    """Construct a runtime from the Click context."""

    resolved: ResolvedConfig = ctx.obj["config"]
    logger: logging.Logger = ctx.obj["logger"]
    return CommandRuntime(config=resolved, logger=logger)
