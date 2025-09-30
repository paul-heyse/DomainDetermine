"""Typer CLI entrypoint."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .config import load_model_config, load_prerequisites_config
from .exceptions import PrerequisiteError, WarmupError
from .paths import DemoPaths, RunContext
from .preflight import validate_prerequisites
from .warmup import WarmupRunner, teardown as teardown_services
from .chat import chat_command

app = typer.Typer(help="LLM demo warmup utility")
warmup_app = typer.Typer(help="Warmup orchestration commands")
chat_app = typer.Typer(help="Interactive chat commands")
app.add_typer(warmup_app, name="warmup")
app.add_typer(chat_app, name="chat")


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _paths() -> DemoPaths:
    return DemoPaths(_root())


@warmup_app.command("preflight")
def preflight(
    prereq_config: Path = typer.Option(Path("config/prerequisites.yaml"), help="Prerequisites config path"),
    run_id: Optional[str] = typer.Option(None, help="Override run identifier"),
) -> None:
    paths = _paths()
    context = RunContext.create(paths, run_id)
    config = load_prerequisites_config(paths.root / prereq_config)
    try:
        validate_prerequisites(config, context)
        typer.echo(f"Prerequisites validated. Manifest: {context.prereq_manifest_path}")
    except PrerequisiteError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc


@warmup_app.command("run")
def run(
    config: Path = typer.Option(Path("config/model.yaml"), help="Model config"),
    prereq_config: Path = typer.Option(Path("config/prerequisites.yaml"), help="Prerequisites config"),
    run_id: Optional[str] = typer.Option(None, help="Run identifier"),
    skip_preflight: bool = typer.Option(False, help="Skip prerequisite validation"),
) -> None:
    runner = WarmupRunner(_paths())
    try:
        result = runner.run(
            run_id=run_id,
            prereq_config_path=str(prereq_config),
            model_config_path=str(config),
            skip_preflight=skip_preflight,
        )
        typer.echo(f"Warmup completed with {len(result.responses)} responses. Summary stored in logs.")
    except WarmupError as exc:
        typer.secho(f"Warmup failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc


@warmup_app.command("teardown")
def teardown(
    config: Path = typer.Option(Path("config/model.yaml"), help="Model config"),
) -> None:
    teardown_services(_paths(), model_config_path=str(config))
    typer.echo("Teardown invoked.")


@chat_app.command("start")
def chat(
    config: Path = typer.Option(Path("config/model.yaml"), help="Model config"),
    session_id: Optional[str] = typer.Option(None, help="Transcript session identifier"),
) -> None:
    chat_command(
        root_path=str(_paths().root),
        model_config_path=str(config),
        session_id=session_id,
    )


@warmup_app.command("verify-negative")
def verify_negative(
    config: Path = typer.Option(Path("config/model.yaml"), help="Model config"),
) -> None:
    """Run lightweight negative-path checks to ensure diagnostics fire."""
    paths = _paths()
    warmup_config = load_model_config(paths.root / config)
    warmup_config.model.offline_mode = True
    warmup_config.model.dry_run = False

    runner = WarmupRunner(paths)

    snapshot_path = paths.state / "negative-offline-config.yaml"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    import yaml

    with snapshot_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(warmup_config.model_dump(), handle)

    try:
        runner.run(
            run_id="negative-offline",
            prereq_config_path="config/prerequisites.yaml",
            model_config_path=str(snapshot_path.relative_to(paths.root)),
            skip_preflight=True,
        )
    except WarmupError:
        typer.echo("Offline cache failure correctly raised WarmupError")
    else:
        typer.secho("Expected offline cache failure", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        snapshot_path.unlink(missing_ok=True)

    typer.echo("Negative-path diagnostics validated")


if __name__ == "__main__":  # pragma: no cover
    app()
