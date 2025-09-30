"""CLI application entrypoint built with Typer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

import typer

# Prompt governance utilities
from DomainDetermine.governance.event_log import GovernanceEventLog
from DomainDetermine.governance.versioning import ChangeImpact
from DomainDetermine.prompt_pack.registry import (
    PromptManifest,
    PromptRegistry,
    PromptRegistryError,
)
from DomainDetermine.prompt_pack.versioning import PromptVersionManager

from .config import ResolvedConfig, load_cli_config, write_current_context
from .logging import configure_logging
from .operations import CommandRuntime, OperationExecutor, build_runtime
from .plugins import PluginExecutionError, describe_plugin_trust
from .plugins import registry as plugin_registry
from .profiles import (
    PATH_ARGUMENT_KEYS,
    ensure_version_compat,
    load_profile,
    resolve_profile_path,
    validate_profile,
)
from .safety import (
    PreflightChecks,
    PreflightError,
    ResourceGuard,
    require_confirmation,
    validate_credentials_reference,
)

# Mapping pipeline integration is optional and configured via register_mapping_pipeline_builder.

CLI_VERSION = "0.1.0"

app = typer.Typer(help="DomainDetermine command line interface")
context_app = typer.Typer(help="Manage CLI contexts")
plugins_app = typer.Typer(help="Inspect and manage CLI plugins")
profile_app = typer.Typer(help="Execute bundled CLI profiles")
prompt_app = typer.Typer(help="Prompt pack governance operations")

app.add_typer(context_app, name="context")
app.add_typer(plugins_app, name="plugins")
app.add_typer(profile_app, name="profile")
app.add_typer(prompt_app, name="prompt")


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
# Prompt governance commands
# ---------------------------------------------------------------------------


@prompt_app.command("bump-version")
def bump_prompt_version(
    template_id: str = typer.Argument(..., help="Prompt template identifier."),
    impact: ChangeImpact = typer.Option(
        ..., "--impact", help="Semantic impact classification (major/minor/patch)."
    ),
    rationale: str = typer.Option(
        ..., "--rationale", help="Summary of the change rationale."
    ),
    owners: List[str] = typer.Option(
        [], "--owner", help="Owner or DRI responsible for the change.", show_default=False
    ),
    metrics: Optional[str] = typer.Option(
        None,
        "--metrics",
        help="JSON object describing expected metric deltas (e.g. '{\"grounding_fidelity\": 0.02}').",
    ),
    approvals: List[str] = typer.Option(
        [], "--approval", help="Recorded approvals for the release.", show_default=False
    ),
    related_manifests: List[str] = typer.Option(
        [],
        "--manifest",
        help="Related governance manifest identifiers to link with this prompt release.",
        show_default=False,
    ),
    prompt_root: Path = typer.Option(
        Path("src/DomainDetermine/prompt_pack"),
        "--root",
        help="Prompt pack root directory containing templates, schemas, and policies.",
        show_default=True,
    ),
    changelog_path: Path = typer.Option(
        Path("docs/prompt_pack/CHANGELOG.md"),
        "--changelog",
        help="Markdown changelog path to append release entries.",
        show_default=True,
    ),
    journal_path: Path = typer.Option(
        Path("docs/prompt_pack/releases.jsonl"),
        "--journal",
        help="JSONL journal recording structured prompt releases.",
        show_default=True,
    ),
    event_log_path: Optional[Path] = typer.Option(
        None,
        "--event-log",
        help="Optional governance event log file for prompt lifecycle events.",
    ),
    actor: str = typer.Option(
        "prompt-governance",
        "--actor",
        help="Actor recorded for governance events.",
        show_default=True,
    ),
) -> None:
    """Validate, hash, and log a prompt version bump."""

    expected_metrics = _parse_metrics(metrics)
    registry = _load_prompt_registry(prompt_root, journal_path)
    event_log: Optional[GovernanceEventLog] = None
    if event_log_path is not None:
        try:
            event_log = GovernanceEventLog(event_log_path)
        except ValueError as exc:
            typer.echo(f"[error] unable to initialise governance event log: {exc}")
            raise typer.Exit(code=1)

    manager = PromptVersionManager(
        prompt_root,
        registry,
        changelog_path=changelog_path,
        journal_path=journal_path,
        event_log=event_log,
    )
    try:
        manifest = manager.publish(
            template_id,
            impact=impact,
            rationale=rationale,
            owners=owners,
            expected_metrics=expected_metrics,
            approvals=approvals,
            actor=actor,
            related_manifests=related_manifests,
        )
    except (PromptRegistryError, FileNotFoundError) as exc:
        typer.echo(f"[error] {exc}")
        raise typer.Exit(code=1)

    reference = manager.reference(manifest)
    typer.echo(
        json.dumps(
            {
                "template_id": manifest.template_id,
                "version": manifest.version,
                "hash": manifest.hash,
                "reference": reference,
                "changelog": str(changelog_path),
                "journal": str(journal_path),
                "event_log": str(event_log_path) if event_log_path else None,
            },
            indent=2,
            sort_keys=True,
        )
    )

def _load_prompt_registry(prompt_root: Path, journal_path: Optional[Path]) -> PromptRegistry:
    """Initialise a prompt registry with optional historical records."""

    registry = PromptRegistry()
    if journal_path and journal_path.exists():
        with journal_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                template_id = record.get("template_id")
                version = record.get("version")
                hash_value = record.get("hash")
                if not (template_id and version and hash_value):
                    continue
                schema_id = record.get("schema_id", "unknown")
                policy_id = record.get("policy_id", "unknown")
                manifest = PromptManifest(
                    template_id=template_id,
                    version=version,
                    schema_id=schema_id,
                    policy_id=policy_id,
                    hash=hash_value,
                )
                registry.register(manifest)
    return registry


def _parse_metrics(payload: Optional[str]) -> Mapping[str, object]:
    if not payload:
        return {}
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Expected JSON for metrics, received error: {exc}")
    if not isinstance(parsed, dict):
        raise typer.BadParameter("Expected metrics to decode into a JSON object")
    return parsed


# ---------------------------------------------------------------------------
# Typer callback
# ---------------------------------------------------------------------------


@app.callback()
def main_callback(
    ctx: typer.Context,
    config: Optional[Path] = typer.Option(None, "--config", help="Path to CLI configuration file (TOML or JSON)."),
    context: Optional[str] = typer.Option(None, "--context", "-c", help="Context name to activate for this invocation."),
    artifact_root: Optional[Path] = typer.Option(None, "--artifact-root", help="Override artifact root for this invocation."),
    registry_url: Optional[str] = typer.Option(None, "--registry-url", help="Override registry URL for this invocation."),
    credentials_ref: Optional[str] = typer.Option(None, "--credentials-ref", help="Override credentials reference identifier."),
    dry_run: bool = typer.Option(
        False,
        "--dry-run/--no-dry-run",
        help="Preview changes without mutating artifacts.",
        show_default=True,
    ),
    log_format: str = typer.Option("text", "--log-format", help="Log format for file output (text or json)."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
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
    ctx.obj = {"config": resolved, "logger": logger, "mapping_pipeline": None}

    if mapping_pipeline_builder is not None:
        ctx.obj["mapping_pipeline"] = mapping_pipeline_builder()


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
        wrappers = plugin_registry.list_plugins(
            cat, runtime.logger, runtime.config.plugin_trust
        )
        typer.echo(f"[{cat}]")
        if not wrappers:
            typer.echo("  (none)")
        else:
            for wrapper in wrappers:
                trust_label = describe_plugin_trust(wrapper, runtime.config.plugin_trust)
                status_suffix = "" if trust_label == "trusted" else f" [{trust_label}]"
                typer.echo(f"  - {wrapper.name} (v{wrapper.version}){status_suffix}")
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
    validation_errors = validate_profile(manifest, _command_callable)
    if validation_errors:
        for error in validation_errors:
            runtime.logger.error(
                "Profile validation error",
                extra={"profile": manifest.name, "error": error},
            )
        formatted = "; ".join(validation_errors)
        raise typer.BadParameter(f"Profile manifest validation failed: {formatted}")

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
def calibrate_mapping(
    ctx: typer.Context,
    mapping_file: Path = typer.Argument(..., help="Mapping configuration"),
    gold: Path = typer.Argument(..., help="Calibration examples (JSONLines or JSON)"),
) -> None:
    runtime = build_runtime(ctx)
    payload = {
        "mapping_file": mapping_file,
        "gold": gold,
        "hash": _hash_path(gold),
    }

    def performer() -> Optional[Path]:
        from DomainDetermine.mapping import MappingContext
        from DomainDetermine.mapping.calibration import CalibrationExample, MappingCalibrationSuite

        entries = json.loads(gold.read_text(encoding="utf-8"))
        if isinstance(entries, dict):
            entries = entries.get("examples", [])
        gold_entries = [
            CalibrationExample(
                text=record["text"],
                expected_concept_id=record["expected_concept_id"],
                context=MappingContext(facets=record.get("facets", {})),
            )
            for record in entries
        ]

        pipeline = ctx.obj.get("mapping_pipeline")
        if pipeline is None:
            raise typer.BadParameter("Mapping pipeline is not configured in CLI context")
        suite = MappingCalibrationSuite(pipeline)
        result = suite.run(gold_entries)
        metrics_path = runtime.artifact_root / "calibration" / f"{_slug(mapping_file.stem)}.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "total": result.total,
            "resolved": result.resolved,
            "correct": result.correct,
            "metrics": dict(result.metrics),
        }
        metrics_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return metrics_path

    _execute_command(ctx, "calibrate_mapping", str(mapping_file), payload, runtime=runtime, performer=performer)


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

mapping_pipeline_builder: Optional[Callable[[], object]] = None


def register_mapping_pipeline_builder(factory: Callable[[], object]) -> None:
    """Register a factory used to build the mapping pipeline for CLI commands."""

    global mapping_pipeline_builder
    mapping_pipeline_builder = factory


def main() -> None:
    """Entrypoint for the CLI."""

    app()
