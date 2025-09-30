## ADDED Requirements
### Requirement: Qwen3 Engine Build Governance
The system SHALL provide a governed build pipeline for the Qwen3-32B W4A8 TensorRT-LLM engine, including containerized environment setup, model snapshot metadata, reproducible build scripts, and manifest capture.

#### Scenario: Engine build manifest recorded
- **WHEN** the engine build completes
- **THEN** the system SHALL persist a manifest recording Hugging Face model commit, tokenizer hash, quantization method (W4A8), trtllm-build flags (`--use_paged_context_fmha`, `--kv_cache_type paged`), max token/batch parameters, calibration dataset hash, and the resulting engine hash

### Requirement: Build Environment Control
The build process SHALL use pinned NVIDIA NGC TensorRT-LLM containers aligned with the serving backend, documenting required driver/CUDA versions and container tags.

#### Scenario: Build launched with mismatched container tag
- **WHEN** a developer attempts to run the build scripts with a container tag that does not match the approved TensorRT-LLM release
- **THEN** the tooling SHALL fail with a clear error directing them to the supported tag list

### Requirement: Build Validation Checks
The pipeline SHALL execute smoke tests (prefill + generation) against the compiled engine inside the container, including deterministic JSON output verification for guided decoding workloads.

#### Scenario: Smoke test failure
- **WHEN** the validation tests fail to reproduce reference outputs
- **THEN** the build SHALL be marked invalid and the manifest SHALL not be published to the registry
