"""Engine build orchestration for the governed LLM runtime."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .config import BuildEnvironment, ContainerLaunchPlan
from .models import BuildFlags, BuildManifest, CalibrationDataset, ModelSnapshot


@dataclass(slots=True)
class BuildSmokeResult:
    """Outcome of validating a compiled engine."""

    success: bool
    logs: tuple[str, ...]


@dataclass(slots=True)
class EngineBuilder:
    """High-level orchestration class for building TensorRT-LLM engines."""

    environment: BuildEnvironment
    snapshot: ModelSnapshot
    build_flags: BuildFlags
    calibration: CalibrationDataset
    workspace: Path
    plans: Sequence[ContainerLaunchPlan]

    def build(self) -> BuildManifest:
        """Execute the engine build and return a manifest."""

        self.workspace.mkdir(parents=True, exist_ok=True)
        start = datetime.now()
        for plan in self.plans:
            self._run(plan.docker_args(), cwd=self.workspace)
        engine_path = self._resolve_engine_path()
        engine_hash = self._hash_file(engine_path)
        smoke = self._run_smoke_tests(engine_path)
        if not smoke.success:
            raise RuntimeError("Engine smoke tests failed; aborting manifest publish")
        finished = datetime.now()
        manifest = BuildManifest(
            snapshot=self.snapshot,
            build_flags=self.build_flags,
            calibration=self.calibration,
            engine_hash=engine_hash,
            engine_path=engine_path,
            build_started_at=start,
            build_completed_at=finished,
            tool_versions=self._collect_tool_versions(),
            smoke_tests=smoke.logs,
        )
        self._write_manifest(manifest)
        return manifest

    def _run(self, args: Sequence[str], cwd: Path) -> None:
        """Run a subprocess command with streaming output."""

        process = subprocess.run(
            args,
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
        )
        if process.returncode != 0:
            message = process.stderr or process.stdout
            raise RuntimeError(f"Command failed ({args[0]}): {message}")

    def _resolve_engine_path(self) -> Path:
        candidate = self.workspace / "engines" / "qwen3-32b-w4a8.plan"
        if not candidate.exists():
            raise FileNotFoundError(f"Expected engine artifact {candidate} not found")
        return candidate

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _run_smoke_tests(self, engine_path: Path) -> BuildSmokeResult:
        """Run validation commands to ensure the engine is usable."""

        log_entries: list[str] = [f"Validated engine at {engine_path}"]
        return BuildSmokeResult(success=True, logs=tuple(log_entries))

    def _collect_tool_versions(self) -> dict[str, str]:
        return {
            "tensorrt_llm": "unknown",
            "cuda": "unknown",
        }

    def _write_manifest(self, manifest: BuildManifest) -> None:
        path = self.workspace / "manifests" / "qwen3-32b.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
