"""Model acquisition and cache management."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from huggingface_hub import snapshot_download

from .config import ModelConfig
from .exceptions import DownloadError
from .paths import RunContext
from .telemetry import append_stage_log, record_cache_manifest
from .utils import read_json, sha256_of_path, write_json


logger = logging.getLogger(__name__)


def _sanitize_cache_dir(cache_root: Path, cache_key: str) -> Path:
    folder_name = cache_key.replace("/", "_").replace(":", "_")
    return cache_root / folder_name


def _load_manifest(context: RunContext) -> Dict[str, Any]:
    manifest = read_json(context.cache_manifest_path)
    manifest.setdefault("entries", [])
    return manifest


def _persist_manifest(context: RunContext, manifest: Dict[str, Any]) -> None:
    record_cache_manifest(context, {"entries": manifest.get("entries", [])})


def _find_entry(entries: List[Dict[str, Any]], cache_key: str) -> Dict[str, Any] | None:
    for entry in entries:
        if entry.get("cache_key") == cache_key:
            return entry
    return None


def download_model(model_config: ModelConfig, context: RunContext) -> Path:
    context.ensure_run_dirs()
    cache_root = (context.paths.root / model_config.cache.path).resolve()
    cache_root.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest(context)
    entries: List[Dict[str, Any]] = manifest.get("entries", [])
    entry = _find_entry(entries, model_config.cache_key)

    now = datetime.utcnow()
    expiry_threshold = now - timedelta(hours=model_config.cache.ttl_hours)

    if entry:
        entry_path = Path(entry["path"])
        entry["expired"] = entry.get("created_at") < expiry_threshold.isoformat()
        append_stage_log(
            context.download_log_path,
            {
                "event": "cache_lookup",
                "cache_key": model_config.cache_key,
                "path": str(entry_path),
                "expired": entry["expired"],
            },
        )
        if entry_path.exists() and not entry["expired"]:
            logger.info("Cache hit for %s", model_config.cache_key)
            append_stage_log(
                context.download_log_path,
                {
                    "event": "cache_hit",
                    "cache_key": model_config.cache_key,
                },
            )
            return entry_path
        if model_config.offline_mode:
            raise DownloadError(
                "Cache expired or missing for offline run; re-run warmup with network access."
            )

    if model_config.offline_mode:
        raise DownloadError("No cached model available for offline mode")

    if model_config.dry_run:
        logger.info("Dry-run enabled; creating placeholder cache for %s", model_config.cache_key)
        target_dir = _sanitize_cache_dir(cache_root, model_config.cache_key)
        target_dir.mkdir(parents=True, exist_ok=True)
        placeholder = target_dir / "PLACEHOLDER"
        placeholder.write_text("dry-run placeholder", encoding="utf-8")
    else:
        logger.info("Downloading model %s", model_config.identifier)
        target_dir = Path(
            snapshot_download(
                repo_id=model_config.identifier,
                revision=model_config.revision,
                local_dir=_sanitize_cache_dir(cache_root, model_config.cache_key),
                local_dir_use_symlinks=False,
                token=None,
            )
        )

    entry_data = {
        "cache_key": model_config.cache_key,
        "path": str(target_dir),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=model_config.cache.ttl_hours)).isoformat(),
        "sha256": sha256_of_path(target_dir),
    }

    if entry:
        entries.remove(entry)
    entries.append(entry_data)
    manifest["entries"] = entries
    _persist_manifest(context, manifest)

    append_stage_log(
        context.download_log_path,
        {
            "event": "download_complete",
            "cache_key": model_config.cache_key,
            "path": str(target_dir),
        },
    )
    return target_dir
