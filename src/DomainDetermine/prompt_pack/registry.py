"""Registry utilities for prompt template manifests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Sequence


class PromptRegistryError(RuntimeError):
    """Raised when prompt registry lookups or references fail."""


@dataclass(frozen=True)
class PromptManifest:
    """Manifest entry for a prompt template."""

    template_id: str
    version: str
    schema_id: str
    policy_id: str
    hash: str


class PromptRegistry:
    """In-memory registry storing prompt manifest entries."""

    def __init__(self) -> None:
        self._entries: Dict[str, PromptManifest] = {}

    def register(self, manifest: PromptManifest) -> None:
        key = _registry_key(manifest.template_id, manifest.version)
        self._entries[key] = manifest

    def get(self, template_id: str, version: str) -> PromptManifest:
        key = _registry_key(template_id, version)
        try:
            return self._entries[key]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise PromptRegistryError(
                f"Prompt {template_id}:{version} is not registered",
            ) from exc

    def resolve(self, template_id: str, version: str) -> PromptManifest | None:
        """Return the manifest for a template/version if registered."""

        key = _registry_key(template_id, version)
        return self._entries.get(key)

    def list_all(self) -> Mapping[str, PromptManifest]:
        return self._entries.copy()

    def latest_version(self, template_id: str) -> str | None:
        """Return the highest semantic version registered for the template."""

        versions = [
            manifest.version
            for manifest in self._entries.values()
            if manifest.template_id == template_id
        ]
        if not versions:
            return None
        return max(versions, key=_version_key)

    def references_for(self, template_id: str) -> Sequence[str]:
        """Return reference strings for all registered versions of a template."""

        refs = [
            format_prompt_reference(manifest)
            for manifest in self._entries.values()
            if manifest.template_id == template_id
        ]
        return tuple(sorted(refs, key=_reference_version_key))

    def build_reference(self, template_id: str, version: str) -> str:
        """Render a canonical reference string for a registered manifest."""

        manifest = self.resolve(template_id, version)
        if manifest is None:
            raise PromptRegistryError(
                f"Prompt {template_id}:{version} is not registered",
            )
        return format_prompt_reference(manifest)


def _registry_key(template_id: str, version: str) -> str:
    return f"{template_id}:{version}"


def _version_key(version: str) -> tuple[int, int, int]:
    try:
        major, minor, patch = version.split(".")
        return int(major), int(minor), int(patch)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise PromptRegistryError(f"Invalid semantic version '{version}'") from exc


def _reference_version_key(reference: str) -> tuple[int, int, int]:
    _, version, _ = parse_prompt_reference(reference)
    return _version_key(version)


def format_prompt_reference(manifest: PromptManifest) -> str:
    """Return canonical reference string with version and hash."""

    return f"{manifest.template_id}:{manifest.version}#{manifest.hash}"


def parse_prompt_reference(reference: str) -> tuple[str, str, str]:
    """Parse a reference string into template id, version, and hash."""

    if "#" not in reference or ":" not in reference:
        msg = "Prompt reference must be formatted as '<template>:<version>#<hash>'"
        raise PromptRegistryError(msg)
    identity, hash_value = reference.split("#", 1)
    template_id, version = identity.split(":", 1)
    template_id = template_id.strip()
    version = version.strip()
    hash_value = hash_value.strip()
    if not (template_id and version and hash_value):
        msg = "Prompt reference segments cannot be empty"
        raise PromptRegistryError(msg)
    return template_id, version, hash_value


__all__ = [
    "PromptManifest",
    "PromptRegistry",
    "PromptRegistryError",
    "format_prompt_reference",
    "parse_prompt_reference",
]

