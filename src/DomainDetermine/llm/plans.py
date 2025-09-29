"""Build plan helpers for the LLM engine pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .config import BuildEnvironment, ContainerLaunchPlan, NGCContainerSpec
from .models import BuildFlags, CalibrationDataset, ModelSnapshot
from .pipeline import EngineBuilder

APPROVED_TRT_LLM_TAGS = {
    "24.05-trtllm-python-py3",
    "24.06-trtllm-python-py3",
}


def _parse_volumes(values: Iterable[str]) -> tuple[Path, ...]:
    return tuple(Path(value).expanduser().resolve() for value in values)


def _parse_env(values: Iterable[dict[str, str]]) -> tuple[tuple[str, str], ...]:
    return tuple((item["key"], item["value"]) for item in values)


def load_engine_builder(plan_path: Path, workspace: Path) -> EngineBuilder:
    """Load an engine build plan from JSON and return an :class:`EngineBuilder`."""

    data = json.loads(plan_path.read_text())
    container_specs = []
    for spec_data in data["environment"]["containers"]:
        tag = spec_data["tag"]
        if tag not in APPROVED_TRT_LLM_TAGS:
            raise ValueError(
                "Container tag mismatch: "
                f"'{tag}' is not in approved TensorRT-LLM tags {sorted(APPROVED_TRT_LLM_TAGS)}"
            )
        container_specs.append(
            NGCContainerSpec(
                image=spec_data["image"],
                tag=tag,
                cuda_version=spec_data["cuda_version"],
                tensorrt_version=spec_data["tensorrt_version"],
                description=spec_data.get("description", ""),
            )
        )

    env = BuildEnvironment(
        driver_version=data["environment"]["driver_version"],
        gpu_name=data["environment"]["gpu_name"],
        containers=tuple(container_specs),
        volumes=_parse_volumes(data["environment"].get("volumes", [])),
        extra_env=_parse_env(data["environment"].get("extra_env", [])),
    )

    snapshot = ModelSnapshot(
        model_id=data["snapshot"]["model_id"],
        revision=data["snapshot"]["revision"],
        tokenizer_files=_parse_volumes(data["snapshot"].get("tokenizer_files", [])),
        license_acceptance=data["snapshot"]["license_acceptance"],
    )

    flags = BuildFlags(
        use_paged_context_fmha=data["build_flags"]["use_paged_context_fmha"],
        kv_cache_type=data["build_flags"]["kv_cache_type"],
        kv_cache_precision=data["build_flags"].get("kv_cache_precision", "fp8"),
        tokens_per_block=data["build_flags"].get("tokens_per_block", 32),
        max_batch_size=data["build_flags"].get("max_batch_size", 4),
        max_input_tokens=data["build_flags"].get("max_input_tokens", 4096),
        max_output_tokens=data["build_flags"].get("max_output_tokens", 1024),
        additional_args=tuple(data["build_flags"].get("additional_args", [])),
    )

    calibration = CalibrationDataset(
        name=data["calibration"]["name"],
        source_uri=data["calibration"]["source_uri"],
        hash=data["calibration"]["hash"],
    )

    plans = []
    for plan_data in data["plans"]:
        plan_spec = next(spec for spec in container_specs if spec.tag == plan_data["container_tag"])
        plans.append(
            ContainerLaunchPlan(
                spec=plan_spec,
                command=tuple(plan_data["command"]),
                volumes=_parse_volumes(plan_data.get("volumes", [])),
                env=_parse_env(plan_data.get("env", [])),
            )
        )

    return EngineBuilder(
        environment=env,
        snapshot=snapshot,
        build_flags=flags,
        calibration=calibration,
        workspace=workspace,
        plans=tuple(plans),
    )
