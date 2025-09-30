"""Warmup orchestration pipeline."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import httpx

from .config import ModelConfig, WarmupConfig, load_model_config, load_prerequisites_config
from .downloader import download_model
from .engine import build_engine
from .exceptions import InferenceError, WarmupError
from .launcher import Launcher
from .paths import DemoPaths, RunContext
from .preflight import validate_prerequisites
from .telemetry import append_stage_log, collect_gpu_snapshot, record_run_manifest
from .utils import write_json

logger = logging.getLogger(__name__)


@dataclass
class WarmupResult:
    responses: List[str]
    timings: Dict[str, float]


class WarmupRunner:
    def __init__(self, root: DemoPaths) -> None:
        self.paths = root

    def run(
        self,
        *,
        run_id: str | None,
        prereq_config_path: str,
        model_config_path: str,
        skip_preflight: bool = False,
    ) -> WarmupResult:
        context = RunContext.create(self.paths, run_id)
        context.ensure_run_dirs()

        warmup_config = load_model_config(self.paths.root / model_config_path)
        model_config = warmup_config.model
        prereq_config = load_prerequisites_config(self.paths.root / prereq_config_path)

        if not skip_preflight:
            logger.info("Running preflight validation")
            validate_prerequisites(prereq_config, context)

        checkpoints_dir = download_model(model_config, context)
        engine_path = build_engine(model_config, checkpoints_dir, context)

        launcher = Launcher(model_config, context)
        try:
            launcher.start()
            result = self._run_warmup_inference(model_config, context)
        finally:
            launcher.stop()

        self._write_summary(context, model_config, engine_path, result)
        return result

    def _run_warmup_inference(self, model_config: ModelConfig, context: RunContext) -> WarmupResult:
        prompts = model_config.warmup_prompts or [model_config.golden_sample.prompt]
        responses: List[str] = []
        timings: Dict[str, float] = {}
        client_timeout = httpx.Timeout(30.0, connect=5.0)

        pre_snapshot = collect_gpu_snapshot()
        append_stage_log(context.inference_log_path, {"event": "gpu_snapshot_before", "payload": pre_snapshot})

        with httpx.Client(timeout=client_timeout) as client:
            for prompt in prompts:
                start = time.perf_counter()
                if model_config.dry_run:
                    response_text = f"[dry-run response] {prompt[:40]}"
                else:
                    payload = {
                        "inputs": prompt,
                        "parameters": {"max_output_tokens": model_config.tensor_rt_llm.max_output_len},
                    }
                    response = client.post(model_config.endpoints.http, json=payload)
                    if response.status_code >= 400:
                        raise InferenceError(
                            f"Warmup inference failed with status {response.status_code}: {response.text}"
                        )
                    response_json = response.json()
                    if isinstance(response_json, dict) and "outputs" in response_json:
                        response_text = str(response_json["outputs"])
                    else:
                        response_text = response.text
                latency = time.perf_counter() - start
                responses.append(response_text)
                timings[prompt] = latency
                append_stage_log(
                    context.inference_log_path,
                    {
                        "event": "warmup_inference",
                        "prompt": prompt,
                        "latency_s": latency,
                        "response_preview": response_text[:200],
                    },
                )

        post_snapshot = collect_gpu_snapshot()
        append_stage_log(context.inference_log_path, {"event": "gpu_snapshot_after", "payload": post_snapshot})

        golden = model_config.golden_sample
        golden_response = responses[-1] if responses else ""
        if golden.expected_substring and golden.expected_substring not in golden_response:
            if model_config.dry_run:
                logger.warning("Golden substring missing in dry-run response; ignoring for dry run")
            else:
                raise InferenceError(
                    "Golden sample validation failed: "
                    f"expected substring '{golden.expected_substring}'"
                )

        append_stage_log(
            context.inference_log_path,
            {
                "event": "golden_validation",
                "expected": golden.expected_substring,
                "found": golden.expected_substring in golden_response,
            },
        )

        return WarmupResult(responses=responses, timings=timings)

    def _write_summary(self, context: RunContext, model_config: ModelConfig, engine_path: str | Path, result: WarmupResult) -> None:
        summary = {
            "model": model_config.identifier,
            "revision": model_config.revision,
            "precision": model_config.precision,
            "engine_path": str(engine_path),
            "responses": result.responses,
            "timings": result.timings,
        }
        write_json(context.summary_path, summary)
        record_run_manifest(
            context,
            {
                "model": summary,
                "cache_manifest": str(context.cache_manifest_path),
                "engine_manifest": str(context.engine_manifest_path),
                "logs": {
                    "download": str(context.download_log_path),
                    "build": str(context.build_log_path),
                    "launch": str(context.launch_log_path),
                    "inference": str(context.inference_log_path),
                    "cleanup": str(context.cleanup_log_path),
                },
            },
        )


def teardown(root: DemoPaths, *, model_config_path: str) -> None:
    paths = RunContext.create(root)
    warmup_config = load_model_config(root.root / model_config_path)
    launcher = Launcher(warmup_config.model, paths)
    launcher.stop()
    append_stage_log(paths.cleanup_log_path, {"event": "manual_teardown"})


def run_warmup(
    *,
    root_path: str,
    prereq_config: str,
    model_config: str,
    run_id: str | None = None,
    skip_preflight: bool = False,
) -> WarmupResult:
    paths = DemoPaths(Path(root_path).resolve())
    runner = WarmupRunner(paths)
    return runner.run(
        run_id=run_id,
        prereq_config_path=prereq_config,
        model_config_path=model_config,
        skip_preflight=skip_preflight,
    )
