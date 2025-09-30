"""Tests for CLI configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from DomainDetermine.cli.config import load_cli_config


def write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "cli.toml"
    config_path.write_text(
        """
default_context = "dev"

[contexts.dev]
artifact_root = "./artifacts"
registry_url = "https://registry.dev"
log_level = "DEBUG"

[contexts.prod]
artifact_root = "./prod-artifacts"
registry_url = "https://registry.prod"
""",
        encoding="utf-8",
    )
    return config_path


def test_load_cli_config_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    env = {"DD_CONTEXT_HOME": str(tmp_path / "state")}
    resolved = load_cli_config(config_path, env=env)

    assert resolved.context.name == "dev"
    assert resolved.context.registry_url == "https://registry.dev"
    assert resolved.artifact_root.exists()
    assert resolved.config_path == config_path


def test_load_cli_config_override_context(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    env = {"DD_CONTEXT_HOME": str(tmp_path / "state")}
    resolved = load_cli_config(config_path, env=env, overrides={"context": "prod"})

    assert resolved.context.name == "prod"
    assert "prod-artifacts" in str(resolved.artifact_root)


def test_load_cli_config_flag_override(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    resolved = load_cli_config(
        config_path,
        env={"DD_CONTEXT_HOME": str(tmp_path / "state")},
        overrides={
            "artifact_root": tmp_path / "custom",
            "log_format": "json",
            "verbose": True,
        },
    )

    assert resolved.artifact_root == tmp_path / "custom"
    assert resolved.log_format == "json"
    assert resolved.verbose is True



def test_load_cli_config_policy_section(tmp_path: Path) -> None:
    config_path = tmp_path / "cli.toml"
    config_path.write_text(
        """
default_context = "dev"

[contexts.dev]
artifact_root = "./artifacts"
registry_url = "https://registry.dev"

[contexts.dev.policy]
license_flags = ["export-approved", "internal"]
max_batch_size = 200
forbidden_topics = ["classified"]
""",
        encoding="utf-8",
    )

    resolved = load_cli_config(
        config_path,
        env={"DD_CONTEXT_HOME": str(tmp_path / "state")},
    )
    policy = resolved.context.policy
    assert policy.max_batch_size == 200
    assert set(policy.license_flags) == {"export-approved", "internal"}
    assert "classified" in policy.forbidden_topics


def test_env_overrides_policy_guard(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    env = {
        "DD_CONTEXT_HOME": str(tmp_path / "state"),
        "DD_MAX_BATCH_SIZE": "321",
        "DD_LICENSE_FLAGS": "a,b",
    }
    resolved = load_cli_config(config_path, env=env)
    policy = resolved.context.policy
    assert policy.max_batch_size == 321
    assert set(policy.license_flags) == {"a", "b"}


# TODO: implement tests for mapping pipeline configuration


