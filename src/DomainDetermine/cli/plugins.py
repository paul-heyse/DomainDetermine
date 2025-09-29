"""Plugin discovery and execution utilities for the DomainDetermine CLI."""

from __future__ import annotations

import importlib.metadata as metadata
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, runtime_checkable

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

    def list_plugins(self, category: str, logger) -> List[PluginWrapper]:
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
        return sorted(wrappers.values(), key=lambda wrapper: wrapper.name)

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
            for wrapper in self.list_plugins(category, logger):
                if wrapper.name == name:
                    plugin = wrapper
                    break
        if plugin is None:
            raise PluginExecutionError(f"Plugin '{name}' not found in category '{category}'")
        try:
            logger.debug(
                "Executing plugin",
                extra={"category": category, "plugin": name, "payload": payload},
            )
            return plugin.execute(runtime, payload)
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
        )

    raise PluginExecutionError(
        f"Plugin '{entry_point_name or candidate}' does not implement the Plugin protocol"
    )


registry = PluginRegistry()

__all__ = [
    "PluginExecutionError",
    "PluginRegistry",
    "PluginWrapper",
    "registry",
]
