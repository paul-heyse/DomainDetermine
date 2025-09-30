"""TensorRT-LLM engine build orchestration."""
from __future__ import annotations

import logging
from pathlib import Path

from .config import ModelConfig
from .exceptions import EngineBuildError
from .paths import RunContext
from .telemetry import append_stage_log, record_engine_manifest
from .utils import run_command, sha256_of_path


logger = logging.getLogger(__name__)


def build_engine(model_config: ModelConfig, checkpoint_dir: Path, context: RunContext) -> Path:
    context.ensure_run_dirs()
    engine_dir = checkpoint_dir / "trt-engine"
    engine_dir.mkdir(parents=True, exist_ok=True)
    engine_path = engine_dir / "engine.plan"

    if model_config.dry_run:
        logger.info("Dry-run: creating placeholder engine at %s", engine_path)
        engine_path.write_text("placeholder engine", encoding="utf-8")
        append_stage_log(
            context.build_log_path,
            {"event": "dry_run_engine", "engine_path": str(engine_path)},
        )
        record_engine_manifest(
            context,
            {
                "cache_key": model_config.cache_key,
                "engine_path": str(engine_path),
                "dry_run": True,
            },
        )
        return engine_path

    command = [
        "trtllm-build",
        f"--checkpoint={checkpoint_dir}",
        f"--output_dir={engine_dir}",
        f"--max_batch_size={model_config.tensor_rt_llm.max_batch_size}",
        f"--max_input_len={model_config.tensor_rt_llm.max_input_len}",
        f"--max_output_len={model_config.tensor_rt_llm.max_output_len}",
        f"--fp16" if model_config.precision == "fp16" else f"--bf16",
        f"--builder_optimization_level={model_config.tensor_rt_llm.builder_optimization_level}",
        f"--workspace_size={model_config.tensor_rt_llm.workspace_size_gb}G",
    ]
    if model_config.tensor_rt_llm.parallel_build:
        command.append("--parallel_build")
    command.extend(model_config.tensor_rt_llm.extra_flags)

    logger.info("Building TensorRT engine: %s", " ".join(command))
    append_stage_log(
        context.build_log_path,
        {"event": "engine_build_start", "command": command},
    )
    result = run_command(command)
    append_stage_log(
        context.build_log_path,
        {
            "event": "engine_build_finish",
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
        },
    )

    if result.returncode != 0 or not engine_path.exists():
        raise EngineBuildError(f"TensorRT-LLM build failed: {result.stderr}")

    record_engine_manifest(
        context,
        {
            "cache_key": model_config.cache_key,
            "engine_path": str(engine_path),
            "sha256": sha256_of_path(engine_path),
            "dry_run": False,
        },
    )
    return engine_path
