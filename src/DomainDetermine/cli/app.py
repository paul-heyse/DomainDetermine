"""CLI application entrypoint built with Typer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import typer

from .config import ResolvedConfig, load_cli_config, write_current_context
from .logging import configure_logging
from .operations import CommandRuntime, OperationExecutor, build_runtime
from .plugins import PluginExecutionError, registry as plugin_registry
from .profiles import (
    PATH_ARGUMENT_KEYS,
    ensure_version_compat,
    load_profile,
    resolve_profile_path,
)
from .safety import (
    PreflightChecks,
    PreflightError,
    ResourceGuard,
    require_confirmation,
    validate_credentials_reference,
)

CLI_VERSION = "0.1.0"

app = typer.Typer(help="DomainDetermine command line interface")
context_app = typer.Typer(help="Manage CLI contexts")
plugins_app = typer.Typer(help="Inspect and manage CLI plugins")
profile_app = typer.Typer(help="Execute bundled CLI profiles")

app.add_typer(context_app, name="context")
app.add_typer(plugins_app, name="plugins")
app.add_typer(profile_app, name="profile")


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _resolve_config(
    context: Optional[str],
    config: Optional[Path],
    artifact_root: Optional[Path],
    registry_url: Optional[str],
    credentials_ref: Optional[str],
    dry_run: bool,
    log_format: str,
    verbose: bool,
) -> ResolvedConfig:
    if credentials_ref:
        validate_credentials_reference(credentials_ref)

    overrides = {
        "context": context,
        "artifact_root": artifact_root,
        "registry_url": registry_url,
        "credentials_ref": credentials_ref,
        "dry_run": dry_run,
        "log_format": log_format,
        "verbose": verbose,
    }
    overrides = {k: v for k, v in overrides.items() if v not in {None, False, ""}}
    resolved = load_cli_config(config, overrides=overrides)
    state_env = {"DD_CONTEXT_HOME": str(resolved.state_path.parent)}
    write_current_context(state_env, resolved.context.name)
    return resolved


def _normalise_payload(values: Dict[str, Any]) -> Dict[str, Any]:
    normalised: Dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, Path):
            normalised[key] = str(value)
        elif isinstance(value, dict):
            normalised[key] = _normalise_payload(value)
        elif isinstance(value, (list, tuple)):
            normalised[key] = [str(item) if isinstance(item, Path) else item for item in value]
        else:
            normalised[key] = value
    return normalised


def _slug(identifier: str) -> str:
    cleaned = identifier.strip().lower().replace(" ", "-")
    safe = [c if c.isalnum() or c in {"-", "_"} else "-" for c in cleaned]
    collapsed = "".join(safe).strip("-")
    return collapsed or "artifact"


def _hash_path(path: Path) -> str:
    if path.exists() and path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()


def _write_artifact(
    resolved: ResolvedConfig,
    verb: str,
    subject: str,
    payload: Dict[str, Any],
) -> Path:
    artifact_dir = resolved.artifact_root / verb
    artifact_dir.mkdir(parents=True, exist_ok=True)
    subject_path = Path(subject)
    base_name = subject_path.stem if subject_path.suffix else subject_path.name
    artifact_path = artifact_dir / f"{_slug(base_name)}.json"
    artifact_payload = {
        "verb": verb,
        "subject": subject,
        "context": resolved.context.name,
        "inputs": payload,
    }
    artifact_path.write_text(json.dumps(artifact_payload, indent=2, sort_keys=True), encoding="utf-8")
    return artifact_path


def _handle_preflight_error(exc: Exception) -> None:
    typer.echo(f"[error] {exc}")
    raise typer.Exit(code=1)


def _execute_command(
    ctx: typer.Context,
    verb: str,
    subject: str,
    payload: Dict[str, Any],
    *,
    runtime: Optional[CommandRuntime] = None,
    performer: Optional[Callable[[], Optional[Path]]] = None,
) -> None:
    runtime = runtime or build_runtime(ctx)
    executor = OperationExecutor(runtime)
    payload = _normalise_payload(payload)
    preview = f"Would {verb} {subject} with {payload}"

    def default_performer() -> Optional[Path]:
        return _write_artifact(runtime.config, verb, subject, payload)

    executor.run(verb, subject, payload, performer or default_performer, preview)


def _prepare_profile_arguments(arguments: Dict[str, Any]) -> Dict[str, Any]:
    prepared: Dict[str, Any] = {}
    for key, value in arguments.items():
        if key in PATH_ARGUMENT_KEYS and isinstance(value, str):
            prepared[key] = Path(value)
        else:
            prepared[key] = value
    return prepared


def _command_callable(verb: str) -> Callable[..., Any]:
    func = globals().get(verb)
    if not callable(func):
        raise ValueError(f"Command '{verb}' is not available for profiles")
    return func


# ---------------------------------------------------------------------------
# Typer callback
# ---------------------------------------------------------------------------


@app.callback()
def main_callback(
    ctx: typer.Context,
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Path to CLI configuration file (TOML or JSON).",
    ),
    context: Optional[str] = typer.Option(
        None, "--context", "-c", help="Context name to activate for this invocation."
    ),
    artifact_root: Optional[Path] = typer.Option(
        None,
        "--artifact-root",
        help="Override artifact root for this invocation.",
    ),
    registry_url: Optional[str] = typer.Option(
        None,
        "--registry-url",
        help="Override registry URL for this invocation.",
    ),
    credentials_ref: Optional[str] = typer.Option(
        None,
        "--credentials-ref",
        help="Override credentials reference identifier.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without mutating artifacts.",
        is_flag=True,
    ),
    log_format: str = typer.Option(
        "text",
        "--log-format",
        help="Log format for file output (text or json).",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging.",
        is_flag=True,
    ),
) -> None:
    """Top-level callback to resolve configuration and configure logging."""

    resolved = _resolve_config(
        context=context,
        config=config,
        artifact_root=artifact_root,
        registry_url=registry_url,
        credentials_ref=credentials_ref,
        dry_run=dry_run,
        log_format=log_format,
        verbose=verbose,
    )

    log_dir = resolved.artifact_root / "logs"
    log_path = log_dir / "cli.log"
    logger = configure_logging(log_path, resolved.log_format, resolved.verbose)
    ctx.obj = {"config": resolved, "logger": logger}


# ---------------------------------------------------------------------------
# Context commands
# ---------------------------------------------------------------------------


@context_app.command("list")
def context_list(ctx: typer.Context) -> None:
    """List configured contexts."""

    resolved: ResolvedConfig = ctx.obj["config"]
    for name in sorted(resolved.contexts.keys()):
        prefix = "*" if name == resolved.context.name else " "
        typer.echo(f"{prefix} {name}")


@context_app.command("use")
def context_use(ctx: typer.Context, name: str) -> None:
    """Switch to a named context."""

    resolved: ResolvedConfig = ctx.obj["config"]
    if name not in resolved.contexts:
        raise typer.BadParameter(f"Unknown context '{name}'")
    write_current_context({}, name)
    typer.echo(f"Context set to {name} (previous {resolved.context.name})")


@context_app.command("show")
def context_show(ctx: typer.Context, name: Optional[str] = None) -> None:
    """Show effective configuration for a context."""

    resolved: ResolvedConfig = ctx.obj["config"]
    target = name or resolved.context.name
    if target not in resolved.contexts:
        raise typer.BadParameter(f"Unknown context '{target}'")
    ctx_config = resolved.contexts[target]
    payload = {
        "artifact_root": str(ctx_config.artifact_root),
        "registry_url": ctx_config.registry_url,
        "credentials_ref": ctx_config.credentials_ref,
        "log_level": ctx_config.log_level,
        "policy": {
            "license_flags": list(ctx_config.policy.license_flags),
            "forbidden_topics": list(ctx_config.policy.forbidden_topics),
            "max_batch_size": ctx_config.policy.max_batch_size,
        },
    }
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# Plugin commands
# ---------------------------------------------------------------------------


@plugins_app.command("list")
def plugins_list(
    ctx: typer.Context,
    category: Optional[str] = typer.Option(
        None, "-c", "--category", help="Filter by plugin category."
    ),
) -> None:
    """List registered CLI plugins."""

    runtime = build_runtime(ctx)
    categories = [category] if category else list(plugin_registry.categories)
    for idx, cat in enumerate(categories):
        wrappers = plugin_registry.list_plugins(cat, runtime.logger)
        typer.echo(f"[{cat}]")
        if not wrappers:
            typer.echo("  (none)")
        else:
            for wrapper in wrappers:
                typer.echo(f"  - {wrapper.name} (v{wrapper.version})")
        if idx < len(categories) - 1:
            typer.echo("")


# ---------------------------------------------------------------------------
# Profile commands
# ---------------------------------------------------------------------------


@profile_app.command("run")
def profile_run(ctx: typer.Context, identifier: str = typer.Argument(...)) -> None:
    """Execute a named profile manifest."""

    runtime = build_runtime(ctx)
    manifest_path = resolve_profile_path(runtime.config, identifier)
    manifest = load_profile(manifest_path)
    ensure_version_compat(manifest, CLI_VERSION)

    typer.echo(f"Profile: {manifest.name}")
    typer.echo(f"Source: {manifest_path}")
    typer.echo("Steps:")
    for line in manifest.describe():
        typer.echo(f"  {line}")

    if runtime.dry_run:
        typer.echo("[dry-run] Profile execution skipped")
        return

    for step in manifest.steps:
        handler = _command_callable(step.verb)
        args = _prepare_profile_arguments(step.arguments)
        ctx.invoke(handler, **args)


# ---------------------------------------------------------------------------
# Pipeline verbs
# ---------------------------------------------------------------------------


@app.command()
def ingest(
    ctx: typer.Context,
    source: Path = typer.Argument(...),
    loader: Optional[str] = typer.Option(None, help="Optional loader plugin to run."),
) -> None:
    """Run ingestion for a given source configuration."""

    runtime = build_runtime(ctx)
    payload = {
        "source": source,
        "source_hash": _hash_path(source),
        "context": runtime.config.context.name,
    }
    if loader:
        payload["loader"] = loader

    def performer() -> Optional[Path]:
        artifact_path = _write_artifact(runtime.config, "ingest", str(source), _normalise_payload(payload))
        if loader:
            plugin_payload = {
                "source": str(source),
                "artifact": str(artifact_path),
                "context": runtime.config.context.name,
            }
            try:
                plugin_registry.execute(
                    "loaders",
                    loader,
                    runtime,
                    plugin_payload,
                    runtime.logger,
                )
            except PluginExecutionError as exc:
                typer.echo(f"[plugin-error] {exc}")
        return artifact_path

    _execute_command(ctx, "ingest", str(source), payload, runtime=runtime, performer=performer)


@app.command()
def snapshot(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Snapshot identifier"),
    source: Optional[Path] = typer.Option(None, help="Optional source artifact to snapshot"),
) -> None:
    payload = {
        "name": name,
        "source": source,
        "context": ctx.obj["config"].context.name,
    }
    _execute_command(ctx, "snapshot", name, payload)


@app.command()
def plan(
    ctx: typer.Context,
    plan_spec: Path = typer.Argument(..., help="Plan specification file"),
    snapshot_name: Optional[str] = typer.Option(None, help="Snapshot to use as baseline"),
) -> None:
    payload = {
        "plan_spec": plan_spec,
        "snapshot": snapshot_name,
        "hash": _hash_path(plan_spec),
    }
    _execute_command(ctx, "plan", str(plan_spec), payload)


@app.command()
def audit(
    ctx: typer.Context,
    report: Path = typer.Argument(..., help="Audit report to generate"),
    plan_spec: Optional[Path] = typer.Option(None, help="Related plan specification"),
) -> None:
    payload = {
        "report": report,
        "plan": plan_spec,
        "artifact": str(report),
    }
    _execute_command(ctx, "audit", str(report), payload)


@app.command()
def map(
    ctx: typer.Context,
    mapping_file: Path = typer.Argument(..., help="Mapping configuration"),
    batch_size: int = typer.Option(100, help="Batch size for mapping execution"),
    max_batch: Optional[int] = typer.Option(
        None, help="Override the configured max batch guardrail."
    ),
) -> None:
    runtime = build_runtime(ctx)
    guard = ResourceGuard(runtime.config.context.policy)
    try:
        guard.ensure_batch_size(batch_size, max_batch)
    except PreflightError as exc:
        _handle_preflight_error(exc)

    payload = {
        "mapping_file": mapping_file,
        "batch_size": batch_size,
        "hash": _hash_path(mapping_file),
        "timeout": guard.default_timeout,
        "rate_limit_backoff": guard.rate_limit_backoff,
        "override_max_batch": max_batch,
    }
    _execute_command(ctx, "map", str(mapping_file), payload, runtime=runtime)


@app.command()
def expand(
    ctx: typer.Context,
    ontology: Path = typer.Argument(..., help="Ontology expansion configuration"),
) -> None:
    payload = {
        "ontology": ontology,
        "hash": _hash_path(ontology),
    }
    _execute_command(ctx, "expand", str(ontology), payload)


@app.command()
def certify(
    ctx: typer.Context,
    dossier: Path = typer.Argument(..., help="Certification dossier path"),
) -> None:
    payload = {
        "dossier": dossier,
        "hash": _hash_path(dossier),
    }
    _execute_command(ctx, "certify", str(dossier), payload)


@app.command()
def evalgen(
    ctx: typer.Context,
    config: Path = typer.Argument(..., help="Evaluation generation config"),
    sample: int = typer.Option(10, help="Sample size for evaluation generation"),
) -> None:
    payload = {
        "config": config,
        "hash": _hash_path(config),
        "sample": sample,
    }
    _execute_command(ctx, "evalgen", str(config), payload)


@app.command()
def publish(
    ctx: typer.Context,
    artifact: str = typer.Argument(..., help="Artifact identifier to publish"),
    channel: str = typer.Option("stable", help="Publish channel"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt."),
) -> None:
    runtime = build_runtime(ctx)
    payload = {
        "artifact": artifact,
        "channel": channel,
    }
    checks = PreflightChecks(runtime.config.context.policy, runtime.logger)
    try:
        checks.run("publish", payload)
    except PreflightError as exc:
        _handle_preflight_error(exc)
    require_confirmation(yes, f"Publish {artifact} to {channel}?")
    _execute_command(ctx, "publish", artifact, payload, runtime=runtime)


@app.command()
def diff(
    ctx: typer.Context,
    baseline: str = typer.Argument(..., help="Baseline artifact"),
    candidate: str = typer.Argument(..., help="Candidate artifact"),
) -> None:
    subject = f"{baseline}-vs-{candidate}"
    payload = {
        "baseline": baseline,
        "candidate": candidate,
    }
    _execute_command(ctx, "diff", subject, payload)


@app.command()
def rollback(
    ctx: typer.Context,
    artifact: str = typer.Argument(..., help="Artifact identifier to rollback"),
    snapshot_name: Optional[str] = typer.Option(None, help="Snapshot to restore"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt."),
) -> None:
    runtime = build_runtime(ctx)
    payload = {
        "artifact": artifact,
        "snapshot": snapshot_name,
    }
    checks = PreflightChecks(runtime.config.context.policy, runtime.logger)
    try:
        checks.run("rollback", payload)
    except PreflightError as exc:
        _handle_preflight_error(exc)
    require_confirmation(yes, f"Rollback {artifact} to {snapshot_name or 'previous snapshot'}?")
    _execute_command(ctx, "rollback", artifact, payload, runtime=runtime)


@app.command()
def run(
    ctx: typer.Context,
    workflow: Path = typer.Argument(..., help="Workflow file to execute"),
) -> None:
    payload = {
        "workflow": workflow,
        "hash": _hash_path(workflow),
    }
    _execute_command(ctx, "run", str(workflow), payload)


@app.command()
def report(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Report name"),
    format: str = typer.Option("html", help="Output format"),
) -> None:
    payload = {
        "name": name,
        "format": format,
    }
    _execute_command(ctx, "report", name, payload)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """Entrypoint for the CLI."""

    app()


