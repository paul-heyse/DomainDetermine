"""Tests for CLI application wiring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from typer.testing import CliRunner

from DomainDetermine.cli.app import app
from DomainDetermine.cli.plugins import registry as plugin_registry


CONFIG_TEXT = """
default_context = "dev"

[contexts.dev]
artifact_root = "./artifacts"
registry_url = "https://registry.dev"

[contexts.staging]
artifact_root = "./staging-artifacts"
registry_url = "https://registry.staging"
"""


def write_config(tmp_path: Path, text: str = CONFIG_TEXT) -> Path:
    config_path = tmp_path / "cli.toml"
    config_path.write_text(text, encoding="utf-8")
    return config_path


def test_cli_ingest_dry_run(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "--dry-run",
            "ingest",
            str(tmp_path / "sources.json"),
        ],
        env={"DD_CONTEXT_HOME": str(tmp_path / "state")},
    )

    assert result.exit_code == 0
    assert "[dry-run]" in result.stdout


def test_cli_ingest_idempotent(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    sources = tmp_path / "sources.json"
    sources.write_text("{}", encoding="utf-8")

    runner = CliRunner()
    env = {"DD_CONTEXT_HOME": str(tmp_path / "state")}
    first = runner.invoke(
        app,
        ["--config", str(config_path), "ingest", str(sources)],
        env=env,
    )
    assert first.exit_code == 0
    artifact = tmp_path / "artifacts" / "ingest" / f"{sources.stem}.json"
    assert artifact.exists()

    second = runner.invoke(
        app,
        ["--config", str(config_path), "ingest", str(sources)],
        env=env,
    )
    assert second.exit_code == 0
    assert "[no-op]" in second.stdout


def test_cli_context_show_outputs_json(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["--config", str(config_path), "context", "show"],
        env={"DD_CONTEXT_HOME": str(tmp_path / "state")},
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["artifact_root"].endswith("artifacts")
    assert "policy" in payload


def test_cli_logs_json_when_requested(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    sources = tmp_path / "sources.json"
    sources.write_text("{}", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "--log-format",
            "json",
            "ingest",
            str(sources),
        ],
        env={"DD_CONTEXT_HOME": str(tmp_path / "state")},
    )
    assert result.exit_code == 0

    log_path = tmp_path / "artifacts" / "logs" / "cli.log"
    assert log_path.exists()
    lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines and lines[-1].lstrip().startswith("{")


def test_cli_plugin_loader_execution(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    sources = tmp_path / "sources.json"
    sources.write_text("{}", encoding="utf-8")

    marker_dir = tmp_path / "artifacts" / "ingest"

    def sample_loader(runtime, source: str, artifact: str, **_: Dict[str, str]) -> None:
        marker = Path(artifact).with_suffix(".plugin")
        marker.write_text(f"plugin:{source}", encoding="utf-8")

    plugin_registry.register("loaders", sample_loader)
    runner = CliRunner()
    try:
        result = runner.invoke(
            app,
            [
                "--config",
                str(config_path),
                "ingest",
                str(sources),
                "--loader",
                "sample_loader",
            ],
            env={"DD_CONTEXT_HOME": str(tmp_path / "state")},
        )
        assert result.exit_code == 0
        marker_candidates = list(marker_dir.glob("*.plugin"))
        assert marker_candidates, "expected plugin marker file to be created"
        assert "plugin:" in marker_candidates[0].read_text(encoding="utf-8")
    finally:
        plugin_registry.unregister("loaders", "sample_loader")


def test_cli_profile_run_dry_run(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    manifest = tmp_path / "legal.toml"
    manifest.write_text(
        """
name = "legal"
cli_version = "0.1.0"

[[steps]]
verb = "ingest"
source = "data/legal.json"
""",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "--dry-run",
            "profile",
            "run",
            str(manifest),
        ],
        env={"DD_CONTEXT_HOME": str(tmp_path / "state")},
    )

    assert result.exit_code == 0
    assert "Profile:" in result.stdout
    assert "[dry-run] Profile execution skipped" in result.stdout


def test_cli_publish_requires_license_flags(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        text="""
default_context = "dev"

[contexts.dev]
artifact_root = "./artifacts"
registry_url = "https://registry.dev"

[contexts.dev.policy]
license_flags = ["export-approved"]
""",
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["--config", str(config_path), "publish", "plan-v1"],
        env={"DD_CONTEXT_HOME": str(tmp_path / "state")},
    )

    assert result.exit_code == 1
    assert "Missing required license" in result.stdout

    success = runner.invoke(
        app,
        ["--config", str(config_path), "publish", "plan-v1", "--yes"],
        env={
            "DD_CONTEXT_HOME": str(tmp_path / "state"),
            "DD_ACCEPTED_LICENSE_FLAGS": "export-approved",
        },
    )
    assert success.exit_code == 0


def test_cli_map_guardrail_enforcement(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        text="""
default_context = "dev"

[contexts.dev]
artifact_root = "./artifacts"
registry_url = "https://registry.dev"

[contexts.dev.policy]
max_batch_size = 100
""",
    )

    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_text("{}", encoding="utf-8")
    runner = CliRunner()
    env = {"DD_CONTEXT_HOME": str(tmp_path / "state")}

    failure = runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "map",
            str(mapping_file),
            "--batch-size",
            "250",
        ],
        env=env,
    )
    assert failure.exit_code == 1
    assert "Batch size" in failure.stdout

    success = runner.invoke(
        app,
        [
            "--config",
            str(config_path),
            "map",
            str(mapping_file),
            "--batch-size",
            "250",
            "--max-batch",
            "250",
        ],
        env=env,
    )
    assert success.exit_code == 0


