"""Profile manifest loading utilities for the DomainDetermine CLI."""

from __future__ import annotations

import inspect
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence

from typer.models import ArgumentInfo, OptionInfo

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


def validate_profile(
    manifest: ProfileManifest, resolver: Callable[[str], Callable[..., Any]]
) -> List[str]:
    """Validate that profile steps match available commands and required arguments."""

    errors: List[str] = []
    for index, step in enumerate(manifest.steps, start=1):
        try:
            handler = resolver(step.verb)
        except ValueError as exc:
            errors.append(f"Step {index}: {exc}")
            continue

        signature = inspect.signature(handler)
        required_arguments: List[str] = []
        for name, parameter in signature.parameters.items():
            if name == "ctx":
                continue
            if parameter.kind not in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }:
                continue
            default = parameter.default
            is_required = False
            if default is inspect.Signature.empty:
                is_required = True
            elif isinstance(default, ArgumentInfo):
                is_required = default.default is ...  # type: ignore[comparison-overlap]
            elif isinstance(default, OptionInfo):
                is_required = default.default is ...  # type: ignore[comparison-overlap]
            if is_required:
                required_arguments.append(name)

        missing = [arg for arg in required_arguments if arg not in step.arguments]
        if missing:
            errors.append(
                f"Step {index} ({step.verb}): missing required arguments: {', '.join(sorted(missing))}"
            )

        unexpected = [
            key for key in step.arguments.keys() if key not in signature.parameters
        ]
        if unexpected:
            errors.append(
                f"Step {index} ({step.verb}): unexpected arguments: {', '.join(sorted(unexpected))}"
            )

    return errors


__all__ = [
    "PATH_ARGUMENT_KEYS",
    "ProfileManifest",
    "ProfileStep",
    "ensure_version_compat",
    "load_profile",
    "resolve_profile_path",
    "validate_profile",
]
