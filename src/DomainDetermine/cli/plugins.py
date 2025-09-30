"""Plugin discovery and execution utilities for the DomainDetermine CLI."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import hmac
import importlib.metadata as metadata
import inspect
import io
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Tuple, runtime_checkable

from .config import PluginTrustPolicy
from .operations import CommandRuntime

PLUGIN_ENTRY_POINTS: Dict[str, str] = {
    "loaders": "cli.plugins.loaders",
    "mappers": "cli.plugins.mappers",
    "graders": "cli.plugins.graders",
    "renderers": "cli.plugins.report_renderers",
}


class PluginExecutionError(RuntimeError):
    """Raised when executing a plugin fails."""


@runtime_checkable
class Plugin(Protocol):
    """Protocol describing a CLI plugin."""

    name: str
    version: str

    def execute(self, runtime: CommandRuntime, **kwargs: Any) -> Any:  # pragma: no cover - protocol
        ...


@dataclass
class PluginWrapper:
    """Adapter around plugin callables to expose metadata consistently."""

    name: str
    version: str
    category: str
    description: str
    callable: Callable[[CommandRuntime, Dict[str, Any]], Any]
    module: Optional[str]
    origin: Optional[Path]
    digest: Optional[str]
    entry_point: Optional[str]

    def execute(self, runtime: CommandRuntime, payload: Dict[str, Any]) -> Any:
        return self.callable(runtime, payload)


class PluginRegistry:
    """Registry responsible for discovering and executing CLI plugins."""

    def __init__(self) -> None:
        self._manual: Dict[str, Dict[str, PluginWrapper]] = {}

    @property
    def categories(self) -> Iterable[str]:  # pragma: no cover - simple access
        return PLUGIN_ENTRY_POINTS.keys()

    def register(self, category: str, plugin: Plugin | Callable[..., Any]) -> None:
        wrapper = _wrap_plugin(category, plugin)
        self._manual.setdefault(category, {})[wrapper.name] = wrapper

    def unregister(self, category: str, name: str) -> None:
        self._manual.get(category, {}).pop(name, None)

    def list_plugins(
        self,
        category: str,
        logger: logging.Logger,
        trust_policy: Optional[PluginTrustPolicy] = None,
    ) -> List[PluginWrapper]:
        wrappers: Dict[str, PluginWrapper] = dict(self._manual.get(category, {}))
        entry_point_group = PLUGIN_ENTRY_POINTS.get(category)
        if entry_point_group:
            for entry_point in metadata.entry_points(group=entry_point_group):
                if entry_point.name in wrappers:
                    continue
                try:
                    loaded = entry_point.load()
                    wrapper = _wrap_plugin(category, loaded, entry_point.name)
                    wrappers[wrapper.name] = wrapper
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error(
                        "Failed to load plugin",
                        extra={
                            "category": category,
                            "entry_point": entry_point.name,
                            "error": str(exc),
                        },
                    )
        plugins = sorted(wrappers.values(), key=lambda wrapper: wrapper.name)
        if trust_policy and not trust_policy.allow_unsigned:
            for plugin in plugins:
                if _plugin_trust_status(plugin, trust_policy) == "untrusted":
                    logger.warning(
                        "Plugin missing trusted signature",
                        extra={"category": category, "plugin": plugin.name},
                    )
        return plugins

    def execute(
        self,
        category: str,
        name: str,
        runtime: CommandRuntime,
        payload: Dict[str, Any],
        logger,
    ) -> Any:
        plugin = self._manual.get(category, {}).get(name)
        if plugin is None:
            for wrapper in self.list_plugins(category, logger, runtime.config.plugin_trust):
                if wrapper.name == name:
                    plugin = wrapper
                    break
        if plugin is None:
            raise PluginExecutionError(f"Plugin '{name}' not found in category '{category}'")
        _verify_plugin_signature(plugin, runtime.config.plugin_trust, logger)
        try:
            logger.debug(
                "Executing plugin",
                extra={"category": category, "plugin": name, "payload": payload},
            )
            with _plugin_sandbox(plugin, logger):
                sandbox_payload = copy.deepcopy(payload)
                return plugin.execute(runtime, sandbox_payload)
        except Exception as exc:
            logger.error(
                "Plugin execution failed",
                extra={"category": category, "plugin": name, "error": str(exc)},
            )
            raise PluginExecutionError(str(exc)) from exc

    def clear_manual(self) -> None:
        self._manual.clear()


def _wrap_plugin(
    category: str,
    candidate: Plugin | Callable[..., Any],
    entry_point_name: Optional[str] = None,
) -> PluginWrapper:
    module_name, origin = _resolve_origin(candidate)
    digest = _compute_digest(origin)

    if isinstance(candidate, Plugin):
        callable_fn = candidate.execute
        name = getattr(candidate, "name", entry_point_name or candidate.__class__.__name__)
        version = getattr(candidate, "version", "0.0.0")
        description = (candidate.__doc__ or "").strip()
        return PluginWrapper(
            name=name,
            version=version,
            category=category,
            description=description,
            callable=lambda runtime, payload: callable_fn(runtime=runtime, **payload),
            module=module_name,
            origin=origin,
            digest=digest,
            entry_point=entry_point_name,
        )

    if callable(candidate):
        name = getattr(candidate, "name", entry_point_name or candidate.__name__)
        version = getattr(candidate, "version", "0.0.0")
        description = (candidate.__doc__ or "").strip()

        def wrapper(runtime: CommandRuntime, payload: Dict[str, Any]) -> Any:
            return candidate(runtime=runtime, **payload)

        return PluginWrapper(
            name=name,
            version=version,
            category=category,
            description=description,
            callable=wrapper,
            module=module_name,
            origin=origin,
            digest=digest,
            entry_point=entry_point_name,
        )

    raise PluginExecutionError(
        f"Plugin '{entry_point_name or candidate}' does not implement the Plugin protocol"
    )


registry = PluginRegistry()


def _resolve_origin(candidate: Plugin | Callable[..., Any]) -> Tuple[Optional[str], Optional[Path]]:
    obj = candidate
    if isinstance(candidate, Plugin):  # type: ignore[misc]
        obj = candidate  # pragma: no cover - structural fallback
    module = inspect.getmodule(obj)
    module_name = module.__name__ if module else None
    origin = getattr(module, "__file__", None) if module else None
    return module_name, Path(origin).resolve() if origin else None


def _compute_digest(origin: Optional[Path]) -> Optional[str]:
    if origin is None or not origin.exists() or not origin.is_file():
        return None
    try:
        return hashlib.sha256(origin.read_bytes()).hexdigest()
    except OSError:  # pragma: no cover - defensive
        return None


def _plugin_trust_status(
    wrapper: PluginWrapper,
    policy: Optional[PluginTrustPolicy],
) -> str:
    if policy is None:
        return "unknown"
    if policy.allow_unsigned:
        if wrapper.name in policy.signature_allowlist and wrapper.digest:
            expected = policy.signature_allowlist[wrapper.name]
            return "trusted" if hmac.compare_digest(wrapper.digest, expected) else "signature-mismatch"
        return "unsigned"
    expected = policy.signature_allowlist.get(wrapper.name)
    if expected is None:
        return "untrusted"
    if wrapper.digest is None:
        return "unsigned"
    return "trusted" if hmac.compare_digest(wrapper.digest, expected) else "signature-mismatch"


def _verify_plugin_signature(
    wrapper: PluginWrapper,
    policy: Optional[PluginTrustPolicy],
    logger: logging.Logger,
) -> None:
    status = _plugin_trust_status(wrapper, policy)
    if status in {"unknown", "unsigned", "trusted"}:
        return
    if status == "signature-mismatch":
        logger.error(
            "Plugin signature mismatch",
            extra={"plugin": wrapper.name, "digest": wrapper.digest, "expected": policy.signature_allowlist.get(wrapper.name) if policy else None},
        )
        raise PluginExecutionError(
            f"Plugin '{wrapper.name}' failed signature verification"
        )
    if status == "untrusted":
        logger.error(
            "Plugin not in signature allowlist",
            extra={"plugin": wrapper.name},
        )
        raise PluginExecutionError(
            f"Plugin '{wrapper.name}' is not trusted. Configure a signature allowlist or enable unsigned plugins."
        )


def describe_plugin_trust(
    wrapper: PluginWrapper,
    policy: Optional[PluginTrustPolicy],
) -> str:
    """Return a human-readable trust status label for CLI output."""

    status = _plugin_trust_status(wrapper, policy)
    if status == "trusted":
        return "trusted"
    if status == "signature-mismatch":
        return "signature-mismatch"
    if status == "untrusted":
        return "untrusted"
    if status == "unsigned":
        return "unsigned"
    return "unknown"


@contextlib.contextmanager
def _plugin_sandbox(plugin: PluginWrapper, logger: logging.Logger):
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    previous_flag = os.environ.get("DD_PLUGIN_SANDBOX")
    previous_dir = os.environ.get("DD_PLUGIN_SANDBOX_DIR")
    with tempfile.TemporaryDirectory(prefix=f"dd-plugin-{plugin.name}-") as sandbox_dir:
        os.environ["DD_PLUGIN_SANDBOX"] = "1"
        os.environ["DD_PLUGIN_SANDBOX_DIR"] = sandbox_dir
        try:
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(
                stderr_buffer
            ):
                yield Path(sandbox_dir)
        finally:
            if previous_flag is None:
                os.environ.pop("DD_PLUGIN_SANDBOX", None)
            else:
                os.environ["DD_PLUGIN_SANDBOX"] = previous_flag
            if previous_dir is None:
                os.environ.pop("DD_PLUGIN_SANDBOX_DIR", None)
            else:
                os.environ["DD_PLUGIN_SANDBOX_DIR"] = previous_dir
            stdout_value = stdout_buffer.getvalue().strip()
            stderr_value = stderr_buffer.getvalue().strip()
            if stdout_value:
                logger.debug(
                    "Plugin stdout captured",
                    extra={"plugin": plugin.name, "stdout": stdout_value},
                )
            if stderr_value:
                logger.warning(
                    "Plugin stderr captured",
                    extra={"plugin": plugin.name, "stderr": stderr_value},
                )


__all__ = [
    "PluginExecutionError",
    "PluginRegistry",
    "PluginWrapper",
    "describe_plugin_trust",
    "registry",
]
