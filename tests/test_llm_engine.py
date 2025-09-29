from __future__ import annotations

import json
from pathlib import Path

import pytest

from DomainDetermine.llm import (
    EngineBuilder,
    default_build_environment,
    default_launch_plan,
    load_engine_builder,
)


@pytest.fixture()
def tmp_plan_dir(tmp_path: Path) -> Path:
    return tmp_path


def write_plan(path: Path, **overrides) -> Path:
    base = {
        "environment": {
            "driver_version": "555.85",
            "gpu_name": "NVIDIA RTX 5090",
            "containers": [
                {
                    "image": "nvcr.io/nvidia/tensorrt-llm/release",
                    "tag": "24.05-trtllm-python-py3",
                    "cuda_version": "12.4",
                    "tensorrt_version": "9.0",
                    "description": "Build container",
                }
            ],
            "volumes": ["/data"],
            "extra_env": [{"key": "CUDA_VISIBLE_DEVICES", "value": "0"}],
        },
        "snapshot": {
            "model_id": "Qwen/Qwen3-32B",
            "revision": "abcdef123456",
            "tokenizer_files": ["/data/tokenizer.json"],
            "license_acceptance": "accepted",
        },
        "build_flags": {
            "use_paged_context_fmha": True,
            "kv_cache_type": "paged",
            "kv_cache_precision": "fp8",
            "tokens_per_block": 32,
            "max_batch_size": 4,
            "max_input_tokens": 4096,
            "max_output_tokens": 512,
            "additional_args": ["--calib-data", "/data/calib.json"],
        },
        "calibration": {
            "name": "synthetic",
            "source_uri": "s3://bucket/calib.json",
            "hash": "deadbeef",
        },
        "plans": [
            {
                "container_tag": "24.05-trtllm-python-py3",
                "command": ["trtllm-build"],
                "volumes": ["/data"],
                "env": [{"key": "HF_HOME", "value": "/data/hf"}],
            }
        ],
    }
    merged = base | overrides
    path.write_text(json.dumps(merged))
    return path


def test_load_engine_builder_success(tmp_plan_dir: Path) -> None:
    plan_path = write_plan(tmp_plan_dir / "plan.json")
    builder = load_engine_builder(plan_path, tmp_plan_dir / "workspace")
    assert isinstance(builder, EngineBuilder)
    assert builder.environment.driver_version == "555.85"
    assert builder.snapshot.model_id == "Qwen/Qwen3-32B"


def test_load_engine_builder_rejects_bad_tag(tmp_plan_dir: Path) -> None:
    plan_path = write_plan(
        tmp_plan_dir / "plan_bad.json",
        environment={
            "driver_version": "555.85",
            "gpu_name": "NVIDIA RTX 5090",
            "containers": [
                {
                    "image": "nvcr.io/nvidia/tensorrt-llm/release",
                    "tag": "bad-tag",
                    "cuda_version": "12.4",
                    "tensorrt_version": "9.0",
                }
            ],
        },
    )
    with pytest.raises(ValueError):
        load_engine_builder(plan_path, tmp_plan_dir / "workspace")


def test_default_build_environment(tmp_path: Path) -> None:
    env = default_build_environment(tmp_path / "artifacts", tmp_path / "cache")
    assert env.driver_version == "555.85"
    assert env.gpu_name == "NVIDIA RTX 5090"
    assert env.containers[0].reference == "nvcr.io/nvidia/tensorrt-llm/release:24.05-trtllm-python-py3"
    assert env.containers[1].reference == "nvcr.io/nvidia/tritonserver:24.05-trtllm-python-py3"


def test_default_launch_plan(tmp_path: Path) -> None:
    plan = default_launch_plan(tmp_path)
    args = plan.docker_args()
    assert "docker" in args[0]
    assert "--gpus" in args
    assert plan.spec.tag == "24.05-trtllm-python-py3"
