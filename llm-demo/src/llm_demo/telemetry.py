"""Telemetry and manifest helpers."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .paths import RunContext
from .utils import read_json, run_command, write_json


def collect_gpu_snapshot() -> Dict[str, Any]:
    if not shutil.which("nvidia-smi"):
        return {"available": False}
    result = run_command(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used,utilization.gpu,driver_version,compute_cap",
            "--format=csv,noheader",
        ]
    )
    if result.returncode != 0:
        return {"available": False, "error": result.stderr.strip()}
    rows = []
    for line in result.stdout.strip().splitlines():
        rows.append([item.strip() for item in line.split(",")])
    return {"available": True, "rows": rows}


def record_prereq_manifest(context: RunContext, payload: Dict[str, Any]) -> None:
    payload_with_meta = {
        **payload,
        "recorded_at": datetime.utcnow().isoformat(),
    }
    write_json(context.prereq_manifest_path, payload_with_meta)


def record_cache_manifest(context: RunContext, payload: Dict[str, Any]) -> None:
    existing = read_json(context.cache_manifest_path)
    existing["entries"] = payload.get("entries", [])
    write_json(context.cache_manifest_path, existing)


def record_engine_manifest(context: RunContext, payload: Dict[str, Any]) -> None:
    write_json(context.engine_manifest_path, {**payload, "recorded_at": datetime.utcnow().isoformat()})


def record_run_manifest(context: RunContext, payload: Dict[str, Any]) -> None:
    enriched = {
        "recorded_at": datetime.utcnow().isoformat(),
        "pid": os.getpid(),
        **payload,
    }
    write_json(context.telemetry_manifest_path, enriched)


def append_stage_log(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


import shutil  # placed at end to avoid circular import issues
