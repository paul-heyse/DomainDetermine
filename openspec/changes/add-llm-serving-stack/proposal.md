## Why
After building the Qwen3-32B TensorRT-LLM engine we need a standardized serving stack using Triton + TRT-LLM backend with guided decoding, paged KV reuse, and in-flight batching so downstream modules can call a single LLM endpoint.

## What Changes
- Define Triton model repository layout and configuration (in-flight batching, KV reuse, guided JSON decoding) for Qwen3-32B.
- Specify container orchestration, startup scripts, and health checks for the Triton TRT-LLM backend.
- Document runtime policies (sampling parameters, guided decoding schemas, return_perf_metrics) and integration hooks.

## Impact
- Affected specs: llm-runtime
- Affected code: deployment manifests, Triton configs, LLM provider interface, observability wiring
