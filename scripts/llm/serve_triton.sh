#!/usr/bin/env bash
# Launch Triton Inference Server with TensorRT-LLM backend for Qwen3-32B.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ENGINE_PATH=${ENGINE_PATH:-${PROJECT_ROOT}/artifacts/engines/qwen3-32b-w4a8.plan}
MODEL_REPO=${MODEL_REPO:-${PROJECT_ROOT}/triton/model_repository}
MODEL_NAME=${MODEL_NAME:-tensorrt_llm}
MODEL_VERSION=${MODEL_VERSION:-1}
TOKENIZER_DIR=${TOKENIZER_DIR:-${PROJECT_ROOT}/artifacts/tokenizer}
TOKENIZER_INFO=${TOKENIZER_INFO:-${PROJECT_ROOT}/artifacts/tokenizer/tokenizer_info.json}
TRITON_IMAGE=${TRITON_IMAGE:-nvcr.io/nvidia/tritonserver:24.05-trtllm-python-py3}
TRITON_HTTP_PORT=${TRITON_HTTP_PORT:-8000}
TRITON_GRPC_PORT=${TRITON_GRPC_PORT:-8001}
TRITON_METRICS_PORT=${TRITON_METRICS_PORT:-8002}
READINESS_MAX_QUEUE_DELAY_US=${READINESS_MAX_QUEUE_DELAY_US:-2500}
READINESS_MAX_TOKENS=${READINESS_MAX_TOKENS:-6000}
READINESS_MAX_COST_USD=${READINESS_MAX_COST_USD:-0.10}

if [[ -z "${READINESS_MAX_QUEUE_DELAY_US}" || -z "${READINESS_MAX_TOKENS}" || -z "${READINESS_MAX_COST_USD}" ]]; then
  echo "[serve_triton] Readiness thresholds missing; using defaults." >&2
fi

if [[ ! -f "${ENGINE_PATH}" ]]; then
  echo "[serve_triton] Engine artifact not found at ${ENGINE_PATH}" >&2
  echo "Set ENGINE_PATH to a valid TensorRT-LLM engine file before running this script." >&2
  exit 1
fi

if [[ ! -d "${TOKENIZER_DIR}" ]]; then
  echo "[serve_triton] Tokenizer directory not found at ${TOKENIZER_DIR}" >&2
  echo "Set TOKENIZER_DIR to the directory containing tokenizer files (e.g., from HF snapshot)." >&2
  exit 1
fi

ENGINE_TARGET="${MODEL_REPO}/${MODEL_NAME}/${MODEL_VERSION}"
mkdir -p "${ENGINE_TARGET}"
cp "${ENGINE_PATH}" "${ENGINE_TARGET}/model.plan"

CONFIG_PATH="${MODEL_REPO}/${MODEL_NAME}/config.pbtxt"
cat > "${CONFIG_PATH}" <<'EOF'
name: "tensorrt_llm"
backend: "tensorrtllm"
max_batch_size: 4

input [
  {
    name: "text_input"
    data_type: TYPE_STRING
    dims: [ -1 ]
  }
]
output [
  {
    name: "text_output"
    data_type: TYPE_STRING
    dims: [ -1 ]
  }
]

instance_group [
  {
    kind: KIND_GPU
    count: 1
  }
]

parameters [
  { key: "guided_decoding_backend" value: { string_value: "xgrammar" } }
  { key: "xgrammar_tokenizer_info_path" value: { string_value: "/workspace/tokenizer/tokenizer_info.json" } }
  { key: "tokenizer_dir" value: { string_value: "/workspace/tokenizer" } }
  { key: "enable_kv_cache_reuse" value: { string_value: "true" } }
  { key: "enable_chunked_context" value: { string_value: "true" } }
  { key: "max_queue_delay_microseconds" value: { string_value: "3000" } }
]
EOF

mkdir -p "$(dirname "${TOKENIZER_INFO}")"
python -m DomainDetermine.llm.tokenizer \
  --tokenizer-dir "${TOKENIZER_DIR}" \
  --output "${TOKENIZER_INFO}"

# Ensure tokenizer assets are available inside workspace mount.
mkdir -p "${PROJECT_ROOT}/workspace/tokenizer"
cp "${TOKENIZER_INFO}" "${PROJECT_ROOT}/workspace/tokenizer/tokenizer_info.json"
rsync -a --delete "${TOKENIZER_DIR}/" "${PROJECT_ROOT}/workspace/tokenizer/"

echo "[serve_triton] Starting Triton server (${TRITON_IMAGE})"
docker run --rm --gpus all \
  -p ${TRITON_HTTP_PORT}:8000 \
  -p ${TRITON_GRPC_PORT}:8001 \
  -p ${TRITON_METRICS_PORT}:8002 \
  -e CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0} \
  -v "${MODEL_REPO}:/models" \
  -v "${PROJECT_ROOT}/workspace:/workspace" \
  ${TRITON_IMAGE} tritonserver --model-repository=/models --log-verbose=0
