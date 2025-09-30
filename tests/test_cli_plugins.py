import hashlib
import inspect
import logging
from pathlib import Path

import pytest

from DomainDetermine.cli.config import (
    ContextConfig,
    ContextPolicy,
    PluginTrustPolicy,
    ResolvedConfig,
)
from DomainDetermine.cli.operations import CommandRuntime
from DomainDetermine.cli.plugins import PluginExecutionError, PluginRegistry


def sample_loader(*, runtime, source: str) -> str:
    runtime.logger.info("Sample loader invoked", extra={"source": source})
    return f"processed:{source}"


def _plugin_digest(func) -> str:
    path = Path(inspect.getfile(func))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_runtime(tmp_path, trust: PluginTrustPolicy) -> CommandRuntime:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    policy = ContextPolicy()
    context = ContextConfig(name="dev", artifact_root=artifact_root, policy=policy)
    resolved = ResolvedConfig(
        context=context,
        contexts={context.name: context},
        dry_run=False,
        log_format="text",
        verbose=False,
        artifact_root=artifact_root,
        config_path=None,
        state_path=tmp_path / "state" / "context",
        raw_overrides={},
        plugin_trust=trust,
    )
    logger = logging.getLogger("test-cli-plugin")
    return CommandRuntime(config=resolved, logger=logger)


def test_plugin_executes_when_signature_trusted(tmp_path):
    registry = PluginRegistry()
    registry.register("loaders", sample_loader)
    digest = _plugin_digest(sample_loader)
    trust = PluginTrustPolicy(allow_unsigned=False, signature_allowlist={"sample_loader": digest})
    runtime = _make_runtime(tmp_path, trust)
    result = registry.execute(
        "loaders",
        "sample_loader",
        runtime,
        {"source": "input.json"},
        runtime.logger,
    )
    assert result == "processed:input.json"


def test_plugin_rejected_when_signature_mismatched(tmp_path):
    registry = PluginRegistry()
    registry.register("loaders", sample_loader)
    trust = PluginTrustPolicy(allow_unsigned=False, signature_allowlist={"sample_loader": "0" * 64})
    runtime = _make_runtime(tmp_path, trust)
    with pytest.raises(PluginExecutionError):
        registry.execute(
            "loaders",
            "sample_loader",
            runtime,
            {"source": "input.json"},
            runtime.logger,
        )


def test_unsigned_plugins_allowed_when_policy_permits(tmp_path):
    registry = PluginRegistry()
    registry.register("loaders", sample_loader)
    trust = PluginTrustPolicy(allow_unsigned=True)
    runtime = _make_runtime(tmp_path, trust)
    result = registry.execute(
        "loaders",
        "sample_loader",
        runtime,
        {"source": "input.json"},
        runtime.logger,
    )
    assert result == "processed:input.json"

