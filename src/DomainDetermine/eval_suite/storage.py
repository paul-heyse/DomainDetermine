"""Governed storage for evaluation suites and results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pyarrow as pa
import pyarrow.parquet as pq

from .models import EvalSuite


@dataclass
class EvalSuiteStorage:
    """Persists suites, manifests, and per-item logs."""

    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def save_suite(self, suite: EvalSuite) -> Path:
        manifest_path = self.root / f"{suite.manifest.suite_id}_{suite.manifest.suite_version}_manifest.parquet"
        table = pa.table(
            {
                "suite_id": [suite.manifest.suite_id],
                "suite_version": [suite.manifest.suite_version],
                "manifest_hash": [suite.manifest.checksum()],
            }
        )
        pq.write_table(table, manifest_path)
        return manifest_path

    def save_slice_metrics(self, suite: EvalSuite, metrics: Mapping[str, Mapping[str, float]]) -> Path:
        metrics_path = self.root / f"{suite.manifest.suite_id}_{suite.manifest.suite_version}_metrics.parquet"
        rows = {
            "suite_id": [],
            "suite_version": [],
            "metric_id": [],
            "value": [],
            "ci_low": [],
            "ci_high": [],
        }
        for metric_id, payload in metrics.items():
            rows["suite_id"].append(suite.manifest.suite_id)
            rows["suite_version"].append(suite.manifest.suite_version)
            rows["metric_id"].append(metric_id)
            rows["value"].append(payload.get("value"))
            rows["ci_low"].append(payload.get("ci_low"))
            rows["ci_high"].append(payload.get("ci_high"))
        table = pa.table(rows)
        pq.write_table(table, metrics_path)
        return metrics_path


