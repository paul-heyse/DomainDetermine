from __future__ import annotations

from pathlib import Path

import yaml

from llm_demo.config import load_model_config, load_prerequisites_config
from llm_demo.downloader import download_model
from llm_demo.exceptions import DownloadError, PrerequisiteError
from llm_demo.paths import DemoPaths, RunContext
from llm_demo.preflight import validate_prerequisites
from llm_demo.warmup import WarmupRunner


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle)


def test_validate_prerequisites_records_manifest(tmp_path: Path) -> None:
    prereq_payload = {
        "hardware": {
            "gpu_architectures": [],
            "min_vram_gb": 0,
            "min_driver_version": "000.0",
        },
        "software": {
            "cuda": {"min_version": "0"},
            "tensorrt": {"min_version": "0"},
            "triton": {"min_version": "0", "image": None},
        },
        "commands": {"required": [{"name": "python"}], "optional": []},
        "environment": {"required": []},
        "files": {"optional": []},
    }
    prereq_path = tmp_path / "config/prereq.yaml"
    _write_yaml(prereq_path, prereq_payload)

    config = load_prerequisites_config(prereq_path)
    paths = DemoPaths(tmp_path)
    context = RunContext.create(paths, run_id="test")

    validate_prerequisites(config, context)
    assert context.prereq_manifest_path.exists()


def test_download_model_dry_run_creates_placeholder(tmp_path: Path) -> None:
    model_payload = {
        "model": {
            "provider": "huggingface",
            "identifier": "dummy/model",
            "tokenizer": "dummy/model",
            "precision": "fp16",
            "tensor_rt_llm": {
                "max_batch_size": 1,
                "max_input_len": 16,
                "max_output_len": 16,
                "builder_optimization_level": 1,
                "workspace_size_gb": 1,
                "parallel_build": False,
                "extra_flags": [],
            },
            "cache": {"ttl_hours": 1, "path": "cache"},
            "offline_mode": False,
            "dry_run": True,
            "requires_auth": False,
            "warmup_prompts": ["hello"],
            "golden_sample": {
                "prompt": "hello",
                "expected_substring": "dry-run",
                "tolerance": 0,
            },
            "endpoints": {
                "http": "http://127.0.0.1:8000",
                "grpc": "127.0.0.1:8001",
                "metrics": "http://127.0.0.1:8002/metrics",
            },
            "launch": {"mode": "docker_compose", "compose_file": "config/docker-compose.yml", "env": {}, "health_timeout_s": 5},
            "redaction_patterns": ["token"],
        }
    }
    model_path = tmp_path / "config/model.yaml"
    _write_yaml(model_path, model_payload)

    config = load_model_config(model_path)
    paths = DemoPaths(tmp_path)
    context = RunContext.create(paths, run_id="run1")

    cache_dir = download_model(config.model, context)
    placeholder = cache_dir / "PLACEHOLDER"
    assert placeholder.exists()
    manifest = context.cache_manifest_path.read_text(encoding="utf-8")
    assert "dummy/model" in manifest


def test_warmup_runner_dry_run(tmp_path: Path) -> None:
    # prepare configs
    prereq_payload = {
        "hardware": {
            "gpu_architectures": [],
            "min_vram_gb": 0,
            "min_driver_version": "000.0",
        },
        "software": {
            "cuda": {"min_version": "0"},
            "tensorrt": {"min_version": "0"},
            "triton": {"min_version": "0", "image": None},
        },
        "commands": {"required": [{"name": "python"}], "optional": []},
        "environment": {"required": []},
        "files": {"optional": []},
    }
    model_payload = {
        "model": {
            "provider": "huggingface",
            "identifier": "dummy/model",
            "tokenizer": "dummy/model",
            "precision": "fp16",
            "tensor_rt_llm": {
                "max_batch_size": 1,
                "max_input_len": 8,
                "max_output_len": 8,
                "builder_optimization_level": 1,
                "workspace_size_gb": 1,
                "parallel_build": False,
                "extra_flags": [],
            },
            "cache": {"ttl_hours": 1, "path": "cache"},
            "offline_mode": False,
            "dry_run": True,
            "requires_auth": False,
            "warmup_prompts": ["ping"],
            "golden_sample": {
                "prompt": "ping",
                "expected_substring": "dry-run",
                "tolerance": 0,
            },
            "endpoints": {
                "http": "http://127.0.0.1:8000",
                "grpc": "127.0.0.1:8001",
                "metrics": "http://127.0.0.1:8002/metrics",
            },
            "launch": {"mode": "docker_compose", "compose_file": "config/docker-compose.yml", "env": {}, "health_timeout_s": 5},
            "redaction_patterns": ["token"],
        }
    }

    prereq_path = tmp_path / "config/prereq.yaml"
    model_path = tmp_path / "config/model.yaml"
    compose_path = tmp_path / "config/docker-compose.yml"
    compose_path.parent.mkdir(parents=True, exist_ok=True)
    compose_path.write_text("version: '3.8'\nservices: {}\n", encoding="utf-8")
    _write_yaml(prereq_path, prereq_payload)
    _write_yaml(model_path, model_payload)

    paths = DemoPaths(tmp_path)
    runner = WarmupRunner(paths)
    result = runner.run(
        run_id="dry-run",
        prereq_config_path=str(prereq_path.relative_to(tmp_path)),
        model_config_path=str(model_path.relative_to(tmp_path)),
        skip_preflight=False,
    )
    assert result.responses
    summary_path = (tmp_path / "logs" / "dry-run" / "summary.json")
    assert summary_path.exists()


def test_offline_mode_without_cache_raises(tmp_path: Path) -> None:
    model_payload = {
        "model": {
            "provider": "huggingface",
            "identifier": "dummy/model",
            "tokenizer": "dummy/model",
            "precision": "fp16",
            "tensor_rt_llm": {
                "max_batch_size": 1,
                "max_input_len": 8,
                "max_output_len": 8,
                "builder_optimization_level": 1,
                "workspace_size_gb": 1,
                "parallel_build": False,
                "extra_flags": [],
            },
            "cache": {"ttl_hours": 1, "path": "cache"},
            "offline_mode": True,
            "dry_run": True,
            "requires_auth": False,
            "warmup_prompts": ["ping"],
            "golden_sample": {
                "prompt": "ping",
                "expected_substring": "dry-run",
                "tolerance": 0,
            },
            "endpoints": {
                "http": "http://127.0.0.1:8000",
                "grpc": "127.0.0.1:8001",
                "metrics": "http://127.0.0.1:8002/metrics",
            },
            "launch": {"mode": "docker_compose", "compose_file": "config/docker-compose.yml", "env": {}, "health_timeout_s": 5},
            "redaction_patterns": ["token"],
        }
    }
    model_path = tmp_path / "config/model.yaml"
    _write_yaml(model_path, model_payload)
    paths = DemoPaths(tmp_path)
    context = RunContext.create(paths, run_id="offline")
    config = load_model_config(model_path)

    try:
        download_model(config.model, context)
    except DownloadError:
        return
    assert False, "Expected DownloadError"


def test_offline_mode_reuses_cache(tmp_path: Path) -> None:
    payload = {
        "model": {
            "provider": "huggingface",
            "identifier": "dummy/model",
            "tokenizer": "dummy/model",
            "precision": "fp16",
            "tensor_rt_llm": {
                "max_batch_size": 1,
                "max_input_len": 8,
                "max_output_len": 8,
                "builder_optimization_level": 1,
                "workspace_size_gb": 1,
                "parallel_build": False,
                "extra_flags": [],
            },
            "cache": {"ttl_hours": 100, "path": "cache"},
            "offline_mode": False,
            "dry_run": True,
            "requires_auth": False,
            "warmup_prompts": ["ping"],
            "golden_sample": {
                "prompt": "ping",
                "expected_substring": "dry-run",
                "tolerance": 0,
            },
            "endpoints": {
                "http": "http://127.0.0.1:8000",
                "grpc": "127.0.0.1:8001",
                "metrics": "http://127.0.0.1:8002/metrics",
            },
            "launch": {"mode": "docker_compose", "compose_file": "config/docker-compose.yml", "env": {}, "health_timeout_s": 5},
            "redaction_patterns": ["token"],
        }
    }
    model_path = tmp_path / "config/model.yaml"
    _write_yaml(model_path, payload)
    paths = DemoPaths(tmp_path)
    context = RunContext.create(paths, run_id="cache")
    config = load_model_config(model_path)

    first_path = download_model(config.model, context)
    assert first_path.exists()

    # toggle offline mode and reuse cache
    config.model.offline_mode = True
    cached_path = download_model(config.model, context)
    assert cached_path == first_path
