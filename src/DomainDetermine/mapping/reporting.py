"""Reporting helpers for mapping artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import MappingBatchResult


@dataclass(slots=True)
class MappingReport:
    """Produces human-readable summaries of mapping batches."""

    output_root: Path

    def write_summary(self, batch: MappingBatchResult) -> Path:
        summary = {
            "metrics": batch.metrics,
            "records": len(batch.records),
            "candidate_logs": len(batch.candidate_logs),
            "crosswalk_proposals": len(batch.crosswalk_proposals),
        }
        path = self.output_root / "summary.json"
        path.write_text(json.dumps(summary, indent=2, sort_keys=True))
        return path

