"""Helpers for computing llm-demo directory structure."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class DemoPaths:
    root: Path

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def state(self) -> Path:
        return self.root / "state"

    @property
    def transcripts(self) -> Path:
        return self.root / "transcripts"

    def ensure(self) -> None:
        for path in (self.cache, self.logs, self.state, self.transcripts):
            path.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class RunContext:
    paths: DemoPaths
    run_id: str

    @classmethod
    def create(cls, paths: DemoPaths, run_id: str | None = None) -> "RunContext":
        paths.ensure()
        resolved_run_id = run_id or datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        return cls(paths=paths, run_id=resolved_run_id)

    @property
    def run_dir(self) -> Path:
        return self.paths.logs / self.run_id

    @property
    def log_dir(self) -> Path:
        return self.run_dir

    @property
    def inference_log_path(self) -> Path:
        return self.run_dir / "inference.jsonl"

    @property
    def summary_path(self) -> Path:
        return self.run_dir / "summary.json"

    @property
    def download_log_path(self) -> Path:
        return self.run_dir / "download.jsonl"

    @property
    def build_log_path(self) -> Path:
        return self.run_dir / "build.log"

    @property
    def launch_log_path(self) -> Path:
        return self.run_dir / "triton.log"

    @property
    def telemetry_manifest_path(self) -> Path:
        return self.paths.state / f"{self.run_id}-manifest.json"

    @property
    def prereq_manifest_path(self) -> Path:
        return self.paths.state / "prereq-manifest.json"

    @property
    def cache_manifest_path(self) -> Path:
        return self.paths.state / "cache-manifest.json"

    @property
    def engine_manifest_path(self) -> Path:
        return self.paths.state / "engine-manifest.json"

    @property
    def cleanup_log_path(self) -> Path:
        return self.run_dir / "cleanup.log"

    def ensure_run_dirs(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
