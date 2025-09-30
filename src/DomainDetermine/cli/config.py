"""Configuration loading utilities for the DomainDetermine CLI."""

from __future__ import annotations

import json
import os
import string
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "domain_determinate" / "cli.toml"
DEFAULT_STATE_HOME = Path.home() / ".domain_determinate"
CONTEXT_FILENAME = "context"


def _expand(path: Optional[str | Path], base: Optional[Path]) -> Optional[Path]:
    if path is None:
        return None
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and base is not None:
        candidate = (base / candidate).resolve()
    return candidate




@dataclass(frozen=True)
class ContextPolicy:
    """Safety-rail configuration for a CLI context."""

    license_flags: tuple[str, ...] = tuple()
    forbidden_topics: tuple[str, ...] = tuple()
    integrity_markers: tuple[Path, ...] = tuple()
    max_batch_size: int = 500
    default_timeout_seconds: int = 300
    rate_limit_backoff: float = 1.5


@dataclass(frozen=True)
class ContextConfig:
    """Configuration specific to a named CLI context."""

    name: str
    artifact_root: Path
    registry_url: Optional[str] = None
    credentials_ref: Optional[str] = None
    log_level: str = "INFO"
    policy: ContextPolicy = field(default_factory=ContextPolicy)


@dataclass(frozen=True)
class CLIConfig:
    """Raw CLI configuration before overrides are applied."""

    contexts: Dict[str, ContextConfig] = field(default_factory=dict)
    default_context: Optional[str] = None
    plugin_trust: "PluginTrustPolicy" = field(default_factory=lambda: PluginTrustPolicy())


@dataclass(frozen=True)
class ResolvedConfig:
    """Final configuration used during a CLI invocation."""

    context: ContextConfig
    contexts: Dict[str, ContextConfig]
    dry_run: bool
    log_format: str
    verbose: bool
    artifact_root: Path
    config_path: Optional[Path]
    state_path: Path
    raw_overrides: Dict[str, Any]
    plugin_trust: "PluginTrustPolicy"


@dataclass(frozen=True)
class PluginTrustPolicy:
    """Control how CLI plugins are validated before execution."""

    allow_unsigned: bool = False
    signature_allowlist: Dict[str, str] = field(default_factory=dict)

    def with_updates(
        self,
        *,
        allow_unsigned: Optional[bool] = None,
        signatures: Optional[Mapping[str, str]] = None,
    ) -> "PluginTrustPolicy":
        updated_signatures = dict(self.signature_allowlist)
        if signatures:
            updated_signatures.update(signatures)
        return PluginTrustPolicy(
            allow_unsigned=self.allow_unsigned if allow_unsigned is None else allow_unsigned,
            signature_allowlist=updated_signatures,
        )


def _parse_policy(data: Optional[Mapping[str, Any]], base_dir: Path) -> ContextPolicy:
    if not data:
        return ContextPolicy()
    license_flags = tuple(
        sorted(filter(None, (flag.strip() for flag in data.get("license_flags", []))))
    )
    forbidden_topics = tuple(
        sorted(filter(None, (topic.strip() for topic in data.get("forbidden_topics", []))))
    )
    integrity_markers = tuple(
        filter(
            None,
            (
                _expand(marker, base_dir)
                for marker in data.get("integrity_markers", []) or []
            ),
        )
    )
    max_batch_size = int(data.get("max_batch_size", ContextPolicy().max_batch_size))
    default_timeout = int(
        data.get("default_timeout_seconds", ContextPolicy().default_timeout_seconds)
    )
    rate_limit_backoff = float(
        data.get("rate_limit_backoff", ContextPolicy().rate_limit_backoff)
    )
    return ContextPolicy(
        license_flags=license_flags,
        forbidden_topics=forbidden_topics,
        integrity_markers=integrity_markers,
        max_batch_size=max_batch_size,
        default_timeout_seconds=default_timeout,
        rate_limit_backoff=rate_limit_backoff,
    )


def _normalise_signature(value: str) -> str:
    token = value.strip().lower()
    if not token:
        raise ValueError("Plugin signature cannot be empty")
    if ":" in token:
        algorithm, digest = token.split(":", 1)
        if algorithm != "sha256":
            raise ValueError("Only sha256 plugin signatures are supported")
        token = digest
    if len(token) != 64 or any(ch not in string.hexdigits for ch in token):
        raise ValueError("Plugin signature must be a 64 character hex digest")
    return token


def _parse_signature_mapping(raw: Mapping[str, Any]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for name, value in raw.items():
        if value is None:
            continue
        mapping[name] = _normalise_signature(str(value))
    return mapping


def _parse_plugin_trust(data: Optional[Mapping[str, Any]]) -> PluginTrustPolicy:
    if not data:
        return PluginTrustPolicy(allow_unsigned=True)
    allow_unsigned = bool(data.get("allow_unsigned", True))
    signatures = _parse_signature_mapping(data.get("signatures", {}))
    return PluginTrustPolicy(allow_unsigned=allow_unsigned, signature_allowlist=signatures)


def _load_file_config(path: Path) -> CLIConfig:
    data: Dict[str, Any]
    suffix = path.suffix.lower()
    content = path.read_bytes()
    if suffix == ".json":
        data = json.loads(content)
    elif suffix in {".toml", ".tml"}:
        data = tomllib.loads(content.decode("utf-8"))
    else:
        raise ValueError(f"Unsupported config format: {path.suffix}")

    default_ctx = data.get("default_context")
    contexts: Dict[str, ContextConfig] = {}
    base_dir = path.parent
    for name, ctx_data in (data.get("contexts") or {}).items():
        artifact_root = _expand(ctx_data.get("artifact_root"), base_dir)
        if artifact_root is None:
            raise ValueError(f"Context '{name}' missing artifact_root")
        policy = _parse_policy(ctx_data.get("policy"), base_dir)
        contexts[name] = ContextConfig(
            name=name,
            artifact_root=artifact_root,
            registry_url=ctx_data.get("registry_url"),
            credentials_ref=ctx_data.get("credentials_ref"),
            log_level=ctx_data.get("log_level", "INFO"),
            policy=policy,
        )

    plugin_trust = _parse_plugin_trust(data.get("plugins"))

    return CLIConfig(contexts=contexts, default_context=default_ctx, plugin_trust=plugin_trust)





def _default_cli_config(base: Path) -> CLIConfig:
    artifact_root = (base / ".artifacts").resolve()
    context = ContextConfig(
        name="dev",
        artifact_root=artifact_root,
        registry_url="https://registry.local.dev",
        log_level="INFO",
    )
    plugin_trust = PluginTrustPolicy(allow_unsigned=True)
    return CLIConfig(
        contexts={context.name: context},
        default_context=context.name,
        plugin_trust=plugin_trust,
    )


def _state_home(env: Mapping[str, str]) -> Path:
    override = env.get("DD_CONTEXT_HOME")
    if override:
        return Path(override).expanduser()
    return DEFAULT_STATE_HOME


def _state_path(env: Mapping[str, str]) -> Path:
    return _state_home(env) / CONTEXT_FILENAME


def read_current_context(env: Mapping[str, str]) -> Optional[str]:
    path = _state_path(env)
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except FileNotFoundError:
        return None


def write_current_context(env: Mapping[str, str], context_name: str) -> None:
    home = _state_home(env)
    home.mkdir(parents=True, exist_ok=True)
    path = home / CONTEXT_FILENAME
    path.write_text(context_name, encoding="utf-8")


def _apply_env_overrides(context: ContextConfig, env: Mapping[str, str]) -> ContextConfig:
    artifact_root = env.get("DD_ARTIFACT_ROOT")
    registry_url = env.get("DD_REGISTRY_URL")
    credentials_ref = env.get("DD_CREDENTIAL_REF")
    log_level = env.get("DD_LOG_LEVEL")

    updated = context
    if artifact_root:
        updated = replace(updated, artifact_root=_expand(artifact_root, None) or updated.artifact_root)
    if registry_url:
        updated = replace(updated, registry_url=registry_url)
    if credentials_ref:
        updated = replace(updated, credentials_ref=credentials_ref)
    if log_level:
        updated = replace(updated, log_level=log_level)

    policy = updated.policy
    license_flags = env.get("DD_LICENSE_FLAGS")
    forbidden_topics = env.get("DD_FORBIDDEN_TOPICS")
    integrity = env.get("DD_INTEGRITY_MARKERS")
    max_batch = env.get("DD_MAX_BATCH_SIZE")
    timeout = env.get("DD_DEFAULT_TIMEOUT")
    backoff = env.get("DD_RATE_LIMIT_BACKOFF")

    changed = False
    if license_flags:
        flags = tuple(sorted(flag.strip() for flag in license_flags.split(",") if flag.strip()))
        policy = replace(policy, license_flags=flags)
        changed = True
    if forbidden_topics:
        topics = tuple(sorted(topic.strip() for topic in forbidden_topics.split(",") if topic.strip()))
        policy = replace(policy, forbidden_topics=topics)
        changed = True
    if integrity:
        markers = tuple(
            filter(
                None,
                (_expand(marker.strip(), None) for marker in integrity.split(":") if marker.strip()),
            )
        )
        policy = replace(policy, integrity_markers=markers)
        changed = True
    if max_batch:
        policy = replace(policy, max_batch_size=int(max_batch))
        changed = True
    if timeout:
        policy = replace(policy, default_timeout_seconds=int(timeout))
        changed = True
    if backoff:
        policy = replace(policy, rate_limit_backoff=float(backoff))
        changed = True
    if changed:
        updated = replace(updated, policy=policy)
    return updated


def _apply_cli_overrides(context: ContextConfig, overrides: Mapping[str, Any]) -> ContextConfig:
    updated = context
    if overrides.get("artifact_root"):
        artifact_root = _expand(overrides["artifact_root"], None)
        if artifact_root is not None:
            updated = replace(updated, artifact_root=artifact_root)
    if overrides.get("registry_url"):
        updated = replace(updated, registry_url=overrides["registry_url"])
    if overrides.get("credentials_ref"):
        updated = replace(updated, credentials_ref=overrides["credentials_ref"])
    if overrides.get("log_level"):
        updated = replace(updated, log_level=overrides["log_level"])
    return updated


def _select_context_name(
    config: CLIConfig,
    env: Mapping[str, str],
    overrides: Mapping[str, Any],
) -> str:
    if overrides.get("context"):
        return overrides["context"]
    if env.get("DD_CONTEXT"):
        return env["DD_CONTEXT"]
    persisted = read_current_context(env)
    if persisted and persisted in config.contexts:
        return persisted
    if config.default_context and config.default_context in config.contexts:
        return config.default_context
    if config.contexts:
        return next(iter(config.contexts.keys()))
    raise ValueError("No CLI contexts have been configured")


def load_cli_config(
    config_path: Optional[Path],
    env: Optional[Mapping[str, str]] = None,
    overrides: Optional[Mapping[str, Any]] = None,
) -> ResolvedConfig:
    env = env or os.environ
    overrides = dict(overrides or {})

    path = config_path or Path(env.get("DD_CLI_CONFIG", "")) or None
    if path:
        path = Path(path).expanduser()
    elif DEFAULT_CONFIG_PATH.exists():
        path = DEFAULT_CONFIG_PATH

    if path and path.exists():
        config = _load_file_config(path)
    else:
        base = Path.cwd()
        config = _default_cli_config(base)
        path = None

    context_name = _select_context_name(config, env, overrides)
    if context_name not in config.contexts:
        raise ValueError(f"Unknown context '{context_name}'")
    context = config.contexts[context_name]
    context = _apply_env_overrides(context, env)
    context = _apply_cli_overrides(context, overrides)

    artifact_root = context.artifact_root
    artifact_root.mkdir(parents=True, exist_ok=True)

    dry_run = bool(overrides.get("dry_run"))
    log_format = (overrides.get("log_format") or env.get("DD_LOG_FORMAT") or "text").lower()
    if log_format not in {"text", "json"}:
        raise ValueError("log_format must be 'text' or 'json'")
    verbose = bool(overrides.get("verbose") or env.get("DD_VERBOSE"))

    state_path = _state_path(env)

    plugin_trust = config.plugin_trust
    allow_unsigned_env = env.get("DD_ALLOW_UNSIGNED_PLUGINS")
    if allow_unsigned_env is not None:
        allow_unsigned = allow_unsigned_env.strip().lower() in {"1", "true", "yes"}
        plugin_trust = plugin_trust.with_updates(allow_unsigned=allow_unsigned)

    signatures_env = env.get("DD_TRUSTED_PLUGIN_SIGNATURES")
    if signatures_env:
        entries = {}
        for item in signatures_env.split(","):
            if not item.strip():
                continue
            if "=" not in item:
                raise ValueError(
                    "DD_TRUSTED_PLUGIN_SIGNATURES entries must use name=sha256 format"
                )
            name, sig = item.split("=", 1)
            entries[name.strip()] = _normalise_signature(sig)
        plugin_trust = plugin_trust.with_updates(signatures=entries)

    return ResolvedConfig(
        context=context,
        contexts=dict(config.contexts),
        dry_run=dry_run,
        log_format=log_format,
        verbose=verbose,
        artifact_root=artifact_root,
        config_path=path,
        state_path=state_path,
        raw_overrides=dict(overrides),
        plugin_trust=plugin_trust,
    )
