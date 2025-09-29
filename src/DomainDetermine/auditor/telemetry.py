"""Telemetry helpers for the coverage auditor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, MutableMapping, Sequence


@dataclass(slots=True)
class AuditTelemetry:
    """Collects telemetry events for audit checks."""

    _events: list[Mapping[str, object]] = field(default_factory=list)

    def record(
        self,
        *,
        metric_name: str,
        value: float | int | str,
        threshold: float | None,
        status: str,
        context: Mapping[str, object],
    ) -> None:
        event: MutableMapping[str, object] = {
            "metric_name": metric_name,
            "value": value,
            "threshold": threshold,
            "status": status,
        }
        event.update(context)
        self._events.append(event)

    def events(self) -> Sequence[Mapping[str, object]]:
        return tuple(self._events)


__all__ = ["AuditTelemetry"]
