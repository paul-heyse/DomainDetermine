# LLM Serving Stack (Triton + TensorRT-LLM)

This guide describes how to deploy the Qwen3-32B W4A8 TensorRT-LLM engine using Triton Inference Server with the TRT-LLM backend. The deployment mirrors the requirements in `add-llm-serving-stack`.

## Containers & Versions

| Component | Image | Tag | Notes |
| --- | --- | --- | --- |
| Triton Server | `nvcr.io/nvidia/tritonserver` | `24.05-trtllm-python-py3` | Bundled TRT-LLM backend |

## Directory Layout

```
artifacts/
  engines/
    qwen3-32b-w4a8.plan
  tokenizer/
    tokenizer.json
triton/
  model_repository/
    tensorrt_llm/
      config.pbtxt
      1/
        model.plan
workspace/
  tokenizer/
    tokenizer_info.json
```

## Scripts

- `scripts/llm/serve_triton.sh`: launches Triton with required mounts (engine, tokenizer). Accepts environment overrides:
  - `ENGINE_PATH` (default `artifacts/engines/qwen3-32b-w4a8.plan`)
  - `MODEL_REPO` (default `triton/model_repository`)
  - `TOKENIZER_DIR`, `TOKENIZER_INFO`
  - `TRITON_IMAGE`, `TRITON_HTTP_PORT`, `TRITON_GRPC_PORT`, `TRITON_METRICS_PORT`
- `scripts/llm/docker-compose.triton.yml`: Docker Compose alternative for long-lived deployment.

## Config Highlights (`config.pbtxt`)

```
parameters [
  { key: "guided_decoding_backend" value: { string_value: "xgrammar" } }
  { key: "xgrammar_tokenizer_info_path" value: { string_value: "/workspace/tokenizer/tokenizer_info.json" } }
  { key: "tokenizer_dir" value: { string_value: "/workspace/tokenizer" } }
  { key: "enable_kv_cache_reuse" value: { string_value: "true" } }
  { key: "enable_chunked_context" value: { string_value: "true" } }
  { key: "max_queue_delay_microseconds" value: { string_value: "3000" } }
]
```

## Runtime Policies

- Default temperatures: `generate_json` (0.0), `rank_candidates` (0.0), `judge` (0.1, top_p 0.9)
- All guided calls include schema ID logging and use the tokenizer info cache
- `return_perf_metrics` enabled for Observability
- `X-Engine-Hash` and `X-Quantisation` headers required; requests missing these are rejected
- Readiness thresholds:
  - `max_queue_delay_us`: 2500 (alerts via readiness webhook)
  - `max_tokens`: 6000 combined prompt + completion
  - `max_cost_usd`: 0.10 per request (finance notified on breach)
- Prompt runtime manifests consumed by Module 6 must reference the same `engine_hash`, tokenizer info hash, and thresholds listed above; use `PromptRuntimeManager.summary()` to verify alignment during sign-off.

## Health & Observability

- Readiness: ensure `

## Capacity Planning

- Target device: RTX 5090 (32 GB). Engine footprint ~18 GB; leave ≥25% headroom for KV cache.
- In-flight batching: max batch size 4. Increase only after verifying queue delay stays under 2.5 ms.
- Chunked context enabled; requests longer than 4k tokens are automatically rejected with `token_budget_overrun` flag.
- Monitor `llm.queue_delay_us`, `llm.tokens_in/out`, and `llm.cost_usd` metrics. Breaches emit `llm_observability_alert` event.
- Rollback: restore previous `model.plan` and manifest, rerun warm-up, log `llm_rollback_completed` with root cause.

## Module 6 & Stakeholder Alignment

- The Eval Blueprint Generator (Module 6) consumes the same engine hash and readiness thresholds documented here (see `docs/eval_suite.md`).
- Before publishing a new engine version, share the build manifest and warm-up results with Module 6 reviewers; they sign off via `llm_observability_alert` summaries on the readiness dashboard.
- Eval slices reference the `engine_hash` and `quantisation` headers enforced by the provider—Module 6 smoke tests must pass prior to promoting the Triton instance to production.
