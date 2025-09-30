# LLM Demo Warmup Prerequisites

This guide lists the infrastructure requirements for running the `llm-demo` warmup sequence. Review these steps before executing `python runner.py warmup run`.

## Hardware

- **GPU architectures:** NVIDIA Ada (SM_89), Hopper (SM_90), or newer with TensorRT-LLM support.
- **Minimum VRAM:** 80 GB for large models; override via `config/model.yaml` for smaller footprints.
- **Host OS:** Ubuntu 22.04 LTS (recommended) with kernel ≥ 6.1 and NVIDIA driver ≥ 555.

## Software stack

- **CUDA toolkit:** 12.4 (matching driver). Install from NVIDIA network repo or container image.
- **TensorRT:** 10.1 or later with TensorRT-LLM python utilities available on the host.
- **TensorRT-LLM Python package:** install via `pip install tensorrt-llm` or conda equivalent.
- **Triton Inference Server:** container image `nvcr.io/nvidia/tritonserver:24.05-py3` or newer.
- **Docker Engine:** 25.x with `nvidia-container-toolkit` configured. Compose v2 plugin recommended.
- **Python dependencies:** Use the project virtual environment (`./.venv`). Ensure `pyyaml`, `httpx`, `typer`, and `rich` are installed.

## Credentials & network

- Hugging Face access token if the model requires authentication (`HF_TOKEN`).
- Local registry credentials for private TensorRT-LLM/Triton images, if applicable.
- Outbound HTTPS access for initial model download; subsequent runs may use offline cache mode.

## Filesystem requirements

- Disk space: model checkpoints + TensorRT engine can exceed 100 GB.
- Writable directories under `llm-demo/cache`, `llm-demo/state`, `llm-demo/logs`, and `llm-demo/transcripts`.

## Validation workflow

1. Activate the project environment (`source .venv/bin/activate`).
2. Run `python runner.py warmup preflight --prereq-config config/prerequisites.yaml` from `llm-demo/`.
3. Resolve any failures surfaced in `state/prereq-manifest.json` before proceeding.
4. Update `config/model.yaml` to select the target model, precision profile, and runtime options.
5. For offline reuse, execute the warmup once with network access, then toggle `offline_mode: true`.

Refer to `config/prerequisites.yaml` for the machine-readable definition consumed by the CLI.
