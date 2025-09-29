## Why
We need a governed workflow to build the Qwen3-32B W4A8 TensorRT-LLM engine on the RTX 5090, pinning model artifacts, quantization choices, and build flags so downstream modules can trust the engine hash.

## What Changes
- Define environment setup using NVIDIA NGC TensorRT-LLM build containers (version pins, driver requirements, volume mounts).
- Specify model snapshot process (Hugging Face commit hash, tokenizer, license acknowledgements) and manifest capture.
- Document the quantization + build pipeline for W4A8 with paged KV cache and FP8 context FMHA, including calibration data handling.
- Capture build manifest fields (input hashes, trtllm-build flags, engine hash) and required validation smoke tests.

## Impact
- Affected specs: llm-runtime
- Affected code: build scripts/runbooks, artifact manifest generators, CI for engine rebuild validation
