"""Safety rails and preflight enforcement for the DomainDetermine CLI."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Optional

import typer

from .config import ContextPolicy


class PreflightError(RuntimeError):
    """Raised when safety checks fail prior to executing a command."""


class PreflightChecks:
    """Run policy-driven preflight checks before mutating operations."""

    def __init__(
        self,
        policy: ContextPolicy,
        logger,
        environment: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._policy = policy
        self._logger = logger
        self._env = environment or os.environ

    def run(self, verb: str, payload: Mapping[str, object]) -> None:
        self._logger.debug("Running preflight checks", extra={"verb": verb})
        self._check_license_flags()
        self._check_forbidden_topics(payload)
        self._check_integrity_markers()

    def _check_license_flags(self) -> None:
        required = set(self._policy.license_flags)
        if not required:
            return
        accepted = {
            flag.strip()
            for flag in self._env.get("DD_ACCEPTED_LICENSE_FLAGS", "").split(",")
            if flag.strip()
        }
        missing = required.difference(accepted)
        if missing:
            self._logger.error(
                "License flags missing",
                extra={"missing_flags": sorted(missing)},
            )
            raise PreflightError(
                "Missing required license acknowledgements: " + ", ".join(sorted(missing))
            )

    def _check_forbidden_topics(self, payload: Mapping[str, object]) -> None:
        topics = {topic.lower() for topic in self._policy.forbidden_topics}
        if not topics:
            return
        scanned = list(_string_values(payload))
        for topic in topics:
            for value in scanned:
                if topic in value.lower():
                    self._logger.error(
                        "Forbidden topic detected",
                        extra={"topic": topic, "value": value},
                    )
                    raise PreflightError(f"Payload references forbidden topic: {topic}")

    def _check_integrity_markers(self) -> None:
        for marker in self._policy.integrity_markers:
            if not marker.exists():
                self._logger.error(
                    "Integrity marker missing",
                    extra={"marker": str(marker)},
                )
                raise PreflightError(f"Integrity marker missing: {marker}")
            if marker.is_file() and marker.stat().st_size == 0:
                self._logger.error(
                    "Integrity marker empty",
                    extra={"marker": str(marker)},
                )
                raise PreflightError(f"Integrity marker empty: {marker}")


class ResourceGuard:
    """Enforces resource guardrails such as batch and timeout limits."""

    def __init__(self, policy: ContextPolicy) -> None:
        self._policy = policy

    @property
    def default_timeout(self) -> int:  # pragma: no cover - trivial
        return self._policy.default_timeout_seconds

    @property
    def rate_limit_backoff(self) -> float:  # pragma: no cover - trivial
        return self._policy.rate_limit_backoff

    def ensure_batch_size(self, batch_size: int, override: Optional[int]) -> None:
        limit = self._policy.max_batch_size
        if batch_size <= limit:
            return
        if override is None:
            raise PreflightError(
                f"Batch size {batch_size} exceeds guardrail {limit}. "
                "Supply --max-batch to acknowledge override."
            )
        if override < batch_size:
            raise PreflightError(
                f"Override {override} is less than requested batch size {batch_size}."
            )


def require_confirmation(assume_yes: bool, prompt: str) -> None:
    """Prompt the operator to confirm a destructive command."""

    if assume_yes:
        return
    confirmed = typer.confirm(prompt, default=False)
    if not confirmed:
        raise typer.Abort()


def validate_credentials_reference(reference: str) -> None:
    """Ensure credential references follow approved secret patterns."""

    if reference.startswith("env:"):
        return
    if "://" in reference:
        return
    raise ValueError(
        "Credentials reference must be an env:VAR token or secret-manager URI."
    )


def _string_values(payload: Mapping[str, object]) -> Iterable[str]:
    for value in payload.values():
        if value is None:
            continue
        if isinstance(value, str):
            yield value
        elif isinstance(value, Path):
            yield str(value)
        elif isinstance(value, Mapping):
            yield from _string_values(value)
        elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
            for item in value:
                if isinstance(item, (str, Path)):
                    yield str(item)


__all__ = [
    "PreflightChecks",
    "PreflightError",
    "ResourceGuard",
    "require_confirmation",
    "validate_credentials_reference",
]
