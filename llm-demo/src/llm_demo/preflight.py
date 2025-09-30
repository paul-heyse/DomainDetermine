"""Host prerequisite validation."""
from __future__ import annotations

import os
from typing import Dict, List

from .config import PrerequisitesConfig
from .exceptions import PrerequisiteError
from .paths import RunContext
from .telemetry import collect_gpu_snapshot, record_prereq_manifest
from .utils import compare_versions, run_command, which


def _driver_version() -> str | None:
    result = run_command(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"])
    if result.returncode != 0:
        return None
    return result.stdout.strip().splitlines()[0]


def _cuda_version() -> str | None:
    result = run_command(["nvcc", "--version"])
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if "release" in line:
            return line.split("release")[-1].split(",")[0].strip()
    return None


def validate_prerequisites(config: PrerequisitesConfig, context: RunContext) -> None:
    failures: List[str] = []
    report: Dict[str, object] = {"commands": [], "environment": [], "files": []}

    for cmd in config.commands.required:
        resolved = which(cmd.name.split()[0])
        ok = resolved is not None
        report["commands"].append({"name": cmd.name, "present": ok})
        if not ok:
            failures.append(f"Missing required command: {cmd.name}")

    for cmd in config.commands.optional:
        resolved = which(cmd.name.split()[0])
        report["commands"].append({"name": cmd.name, "present": resolved is not None, "optional": True})

    for env_var in config.environment.required:
        value = os.environ.get(env_var.name)
        exists = value is not None
        report["environment"].append({"name": env_var.name, "present": exists, "optional": env_var.optional})
        if not exists and not env_var.optional:
            failures.append(f"Missing required environment variable: {env_var.name}")

    for file_spec in config.files.optional:
        exists = file_spec.path.exists()
        report["files"].append({"path": str(file_spec.path), "present": exists})

    driver_version = None
    cuda_version = None
    gpu_snapshot = collect_gpu_snapshot()
    if gpu_snapshot.get("available"):
        driver_version = gpu_snapshot["rows"][0][4]
        if not compare_versions(driver_version, config.hardware.min_driver_version):
            failures.append(
                "Driver version is below minimum: "
                f"found {driver_version}, expected >= {config.hardware.min_driver_version}"
            )

    if which("nvcc"):
        cuda_version = _cuda_version()
        if cuda_version and not compare_versions(cuda_version, config.software.cuda.min_version):
            failures.append(
                f"CUDA version {cuda_version} < required {config.software.cuda.min_version}"
            )

    report.update(
        {
            "driver_version": driver_version,
            "cuda_version": cuda_version,
            "gpu_snapshot": gpu_snapshot,
            "min_driver_version": config.hardware.min_driver_version,
            "min_cuda_version": config.software.cuda.min_version,
        }
    )

    record_prereq_manifest(context, report)

    if failures:
        raise PrerequisiteError("; ".join(failures))
