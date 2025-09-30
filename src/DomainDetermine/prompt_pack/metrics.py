"""Metrics collection utilities for prompt templates."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Mapping, MutableMapping


@dataclass
class TemplateMetrics:
    """Aggregated metrics across locales for a prompt template runtime."""

    template_id: str
    version: str
    counters: MutableMapping[str, MutableMapping[str, float]] = field(default_factory=dict)
    history: MutableMapping[str, list[Mapping[str, float]]] = field(default_factory=dict)

    def record(self, name: str, value: float, *, locale: str = "default") -> None:
        locale_bucket = self.counters.setdefault(locale, {})
        locale_bucket[name] = value

    def increment(self, name: str, delta: float = 1.0, *, locale: str = "default") -> None:
        locale_bucket = self.counters.setdefault(locale, {})
        locale_bucket[name] = locale_bucket.get(name, 0.0) + delta

    def record_metrics(self, metrics: Mapping[str, float], *, locale: str = "default") -> None:
        for metric, value in metrics.items():
            self.record(metric, float(value), locale=locale)

    def track_observation(self, metrics: Mapping[str, float], *, locale: str = "default") -> None:
        observations = self.history.setdefault(locale, [])
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **{metric: float(value) for metric, value in metrics.items()},
        }
        observations.append(payload)
        if len(observations) > 50:
            del observations[0 : len(observations) - 50]

    def as_dict(self) -> Mapping[str, Mapping[str, float]]:
        return {locale: dict(values) for locale, values in self.counters.items()}

    def snapshot(self) -> Mapping[str, object]:
        return {
            "counters": self.as_dict(),
            "history": {locale: list(values) for locale, values in self.history.items()},
        }

    def reset(self) -> None:
        self.counters.clear()
        self.history.clear()


class MetricsRepository:
    """In-memory repository for prompt metrics with simple persistence helpers."""

    def __init__(self) -> None:
        self._store: Dict[str, TemplateMetrics] = {}

    def upsert(self, metrics: TemplateMetrics) -> None:
        key = self._key(metrics.template_id, metrics.version)
        self._store[key] = metrics

    def get(self, template_id: str, version: str) -> TemplateMetrics:
        key = self._key(template_id, version)
        if key not in self._store:
            self._store[key] = TemplateMetrics(template_id, version)
        return self._store[key]

    def record_metrics(
        self,
        *,
        template_id: str,
        version: str,
        metrics: Mapping[str, float],
        locale: str = "default",
        observation: bool = False,
    ) -> TemplateMetrics:
        record = self.get(template_id, version)
        record.record_metrics(metrics, locale=locale)
        if observation:
            record.track_observation(metrics, locale=locale)
        self.upsert(record)
        return record

    def record_quality_sample(
        self,
        *,
        template_id: str,
        version: str,
        locale: str,
        acceptance_rate: float,
        deferral_rate: float,
        grounding_fidelity: float,
        hallucination_rate: float,
        constraint_violations: float,
        latency_ms: float,
        cost_usd: float,
    ) -> TemplateMetrics:
        metrics = {
            "acceptance_rate": acceptance_rate,
            "deferral_rate": deferral_rate,
            "grounding_fidelity": grounding_fidelity,
            "hallucination_rate": hallucination_rate,
            "constraint_violations": constraint_violations,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
        }
        return self.record_metrics(
            template_id=template_id,
            version=version,
            metrics=metrics,
            locale=locale,
            observation=True,
        )

    def snapshot(self) -> Mapping[str, TemplateMetrics]:
        return self._store.copy()

    def reset(self) -> None:
        self._store.clear()

    def as_dict(self) -> Mapping[str, Mapping[str, object]]:
        payload: Dict[str, Mapping[str, object]] = {}
        for key, metrics in self._store.items():
            payload[key] = {
                "template_id": metrics.template_id,
                "version": metrics.version,
                "locales": metrics.as_dict(),
                "history": {locale: list(values) for locale, values in metrics.history.items()},
            }
        return payload

    def persist(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": self.as_dict(),
        }
        path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
        return path

    @staticmethod
    def _key(template_id: str, version: str) -> str:
        return f"{template_id}:{version}"
