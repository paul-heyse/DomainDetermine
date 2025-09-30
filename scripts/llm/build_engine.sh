#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKSPACE="${PROJECT_ROOT}/workspace"
MODEL_DIR="${WORKSPACE}/models/qwen3-32b"
ENGINE_DIR="${WORKSPACE}/engines"
MANIFEST_DIR="${WORKSPACE}/manifests"
CALIB_DIR="${WORKSPACE}/calibration"

mkdir -p "${MODEL_DIR}" "${ENGINE_DIR}" "${MANIFEST_DIR}" "${CALIB_DIR}"

python3 ${PROJECT_ROOT}/tools/llm/download_snapshot.py --model-id Qwen/Qwen3-32B --revision main --output "${MODEL_DIR}"
python3 ${PROJECT_ROOT}/tools/llm/prepare_qwen3.py --input "${MODEL_DIR}" --output "${WORKSPACE}/checkpoints"
python3 ${PROJECT_ROOT}/tools/llm/quantize_awq.py --input "${WORKSPACE}/checkpoints" --output "${WORKSPACE}/quantized" --calibration "${CALIB_DIR}"

trtllm-build \
  --checkpoint-dir "${WORKSPACE}/quantized" \
  --output-dir "${ENGINE_DIR}" \
  --use_paged_context_fmha enable \
  --kv_cache_type paged \
  --kv_cache_precision fp8 \
  --tokens_per_block 32 \
  --max_batch_size 4 \
  --max_input_tokens 4096 \
  --max_output_tokens 1024

python3 ${PROJECT_ROOT}/tools/llm/write_manifest.py --workspace "${WORKSPACE}" --engine "${ENGINE_DIR}/qwen3-32b-w4a8.plan" --output "${MANIFEST_DIR}/qwen3-32b.json"
# Note readiness thresholds for downstream deployment (served via environment variables):
#   READINESS_MAX_QUEUE_DELAY_US=2500
#   READINESS_MAX_TOKENS=6000
#   READINESS_MAX_COST_USD=0.10

python3 ${PROJECT_ROOT}/tools/llm/smoke_test.py --engine "${ENGINE_DIR}/qwen3-32b-w4a8.plan" --output "${WORKSPACE}/smoke/qwen3.json"
