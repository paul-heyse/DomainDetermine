## ADDED Requirements
### Requirement: Triton TRT-LLM Serving Stack
The system SHALL deploy the Qwen3-32B W4A8 TensorRT-LLM engine via Triton Inference Server with the TRT-LLM backend, enabling in-flight batching, paged KV reuse, and guided decoding for schema-constrained outputs.

#### Scenario: Triton configuration validation
- **WHEN** the serving stack is launched
- **THEN** the deployment SHALL load the engine under `tensorrt_llm/1/` with `config.pbtxt` parameters for `batching_strategy: inflight_fused_batching`, `enable_kv_cache_reuse: "true"`, `guided_decoding_backend: "xgrammar"`, and tokenizer info paths

### Requirement: Runtime Policy Enforcement
The LLM provider interface SHALL expose capability methods (`generate_json`, `rank_candidates`, `judge`) that apply approved decoding parameters (low temperature, guided JSON schemas where applicable) and record engine metadata (engine hash, quantization, guided status) in logs.

#### Scenario: Guided JSON request
- **WHEN** a module invokes `generate_json` with a schema
- **THEN** the Triton request SHALL set guided decoding parameters (guide_type/json schema), enforce low temperature, and log the schema version and engine hash for traceability

### Requirement: Operational Runbooks
The deployment SHALL include start/stop scripts, health checks, and rollback instructions referencing specific container tags and model hashes to ensure reproducible operations on the RTX 5090 host.

#### Scenario: Rollback required
- **WHEN** the deployed engine exhibits regressions
- **THEN** operators SHALL follow the documented rollback runbook to redeploy the last known-good engine by tag and manifest hash
