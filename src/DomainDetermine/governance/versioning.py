"""Semantic versioning, hashing, and signing utilities for governance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Mapping, Sequence

from DomainDetermine.governance.models import ArtifactMetadata


class ChangeImpact(str, Enum):
    """Represents a publish impact classification."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class SemanticVersioner:
    """Calculates semantic version bumps for governed artifacts."""

    def next_version(self, previous_version: str | None, impact: ChangeImpact) -> str:
        """Return the next semantic version based on impact."""

        if previous_version is None:
            return self._initial_version(impact)

        major, minor, patch = self._split(previous_version)
        if impact is ChangeImpact.MAJOR:
            major += 1
            minor = 0
            patch = 0
        elif impact is ChangeImpact.MINOR:
            minor += 1
            patch = 0
        else:
            patch += 1
        return f"{major}.{minor}.{patch}"

    @staticmethod
    def _split(version: str) -> tuple[int, int, int]:
        try:
            major, minor, patch = version.split(".")
            return int(major), int(minor), int(patch)
        except (ValueError, AttributeError) as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid semantic version '{version}'") from exc

    @staticmethod
    def _initial_version(impact: ChangeImpact) -> str:
        if impact is ChangeImpact.MAJOR:
            return "1.0.0"
        if impact is ChangeImpact.MINOR:
            return "0.1.0"
        return "0.0.1"


def canonical_payload(payload: Mapping[str, object]) -> str:
    """Return canonical JSON for hashing/signing."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_hash(payload: Mapping[str, object]) -> str:
    """Compute a deterministic SHA-256 hash for a payload."""

    canonical = canonical_payload(payload)
    return sha256(canonical.encode("utf-8")).hexdigest()


def manifest_payload(metadata: ArtifactMetadata) -> Mapping[str, object]:
    """Return canonical payload for hashing of manifests."""

    payload = metadata.to_dict()
    payload["hash"] = ""
    payload["signature"] = ""
    return payload


@dataclass(slots=True)
class SignatureManager:
    """Produces deterministic signatures for artifact manifests."""

    secret: str

    def sign(self, payload_hash: str, *, context: Sequence[str] | None = None) -> str:
        """Return a signature derived from hash, optional context, and secret."""

        fingerprint = sha256()
        fingerprint.update(self.secret.encode("utf-8"))
        fingerprint.update(payload_hash.encode("utf-8"))
        if context:
            for token in context:
                fingerprint.update(token.encode("utf-8"))
        return fingerprint.hexdigest()

    def verify(self, payload_hash: str, signature: str, *, context: Sequence[str] | None = None) -> bool:
        """Verify a signature for the given hash and context."""

        expected = self.sign(payload_hash, context=context)
        return expected == signature


__all__ = [
    "ChangeImpact",
    "SemanticVersioner",
    "SignatureManager",
    "canonical_payload",
    "compute_hash",
    "manifest_payload",
]

