"""Profile manifest loading utilities for the DomainDetermine CLI."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from .config import ResolvedConfig

CLI_VERSION_FALLBACK = "0.1.0"


@dataclass(frozen=True)
class ProfileStep:
    """Represents a single command invocation within a profile."""

    verb: str
    arguments: Dict[str, Any]


@dataclass(frozen=True)
class ProfileManifest:
    """Describes a profile containing multiple CLI steps."""

    name: str
    cli_version: str
    steps: Sequence[ProfileStep]
    description: str = ""

    def describe(self) -> Iterable[str]:
        for index, step in enumerate(self.steps, start=1):
            args = ", ".join(f"{key}={value}" for key, value in step.arguments.items())
            yield f"{index}. {step.verb} {args}" if args else f"{index}. {step.verb}"


PATH_ARGUMENT_KEYS = {
    "source",
    "plan_spec",
    "report",
    "mapping_file",
    "ontology",
    "dossier",
    "config",
    "workflow",
    "manifest",
}


def resolve_profile_path(config: ResolvedConfig, identifier: str) -> Path:
    candidate = Path(identifier)
    if candidate.exists():
        return candidate

    search_candidates: List[Path] = []
    search_candidates.append(config.artifact_root / "profiles" / f"{identifier}.toml")
    if config.config_path:
        search_candidates.append(config.config_path.parent / "profiles" / f"{identifier}.toml")

    for path in search_candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"Profile manifest '{identifier}' not found")


def load_profile(path: Path) -> ProfileManifest:
    if not path.exists():
        raise FileNotFoundError(path)
    data: Dict[str, Any]
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = tomllib.loads(path.read_text(encoding="utf-8"))

    name = data.get("name") or path.stem
    cli_version = data.get("cli_version") or data.get("version") or CLI_VERSION_FALLBACK
    description = data.get("description", "")
    raw_steps = data.get("steps") or []
    if not raw_steps:
        raise ValueError(f"Profile '{name}' contains no steps")

    steps: List[ProfileStep] = []
    for raw in raw_steps:
        if "verb" not in raw:
            raise ValueError("Profile step missing 'verb'")
        verb = raw["verb"]
        arguments = {k: v for k, v in raw.items() if k != "verb"}
        steps.append(ProfileStep(verb=verb, arguments=arguments))

    return ProfileManifest(name=name, cli_version=cli_version, steps=tuple(steps), description=description)


def ensure_version_compat(manifest: ProfileManifest, cli_version: str) -> None:
    if manifest.cli_version != cli_version:
        raise ValueError(
            f"Profile '{manifest.name}' targets CLI {manifest.cli_version} but running {cli_version}"
        )


__all__ = [
    "PATH_ARGUMENT_KEYS",
    "ProfileManifest",
    "ProfileStep",
    "ensure_version_compat",
    "load_profile",
    "resolve_profile_path",
]
