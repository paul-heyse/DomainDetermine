## ADDED Requirements

### Requirement: Documented hardware and runtime prerequisites
The system SHALL ship `llm-demo/docs/prerequisites.md` and a machine-readable `llm-demo/config/prerequisites.yaml` enumerating supported GPU architectures, minimum VRAM, CUDA/TensorRT/Triton versions with container image tags, nvidia-container-toolkit setup steps, disk-space requirements, and mandatory environment variables; the warmup entrypoint SHALL execute these checks and block execution when they fail.

#### Scenario: Prerequisite validation succeeds
- **WHEN** an operator launches the warmup entrypoint on a compliant host
- **THEN** the tool records the validated versions and hardware snapshot under `llm-demo/state/prereq-manifest.json` and proceeds to model acquisition.

#### Scenario: Prerequisite validation fails
- **WHEN** the host lacks a required driver, toolkit, or credential
- **THEN** the tool aborts before download/build, redacts sensitive output, and emits remediation steps referencing `prerequisites.md`.

### Requirement: llm-demo directory isolation
The system SHALL provide an `llm-demo/` directory containing all warmup assets (scripts, configs, docs, manifests) without introducing dependencies on existing production packages and SHALL emit a manifest describing the tooling versions used within the directory.

#### Scenario: Demo assets isolated
- **WHEN** a developer inspects the repository layout
- **THEN** all warmup code, manifests, and documentation reside under `llm-demo/` and do not modify existing application modules.

### Requirement: Configurable model acquisition and caching
The warmup sequence SHALL accept declarative configuration via CLI flags and `llm-demo/config/model.yaml`, capturing the model ID, tokenizer, precision profile, TensorRT-LLM build parameters, credential sources, and cache retention policy; it SHALL download required assets, verify checksums, store metadata in `llm-demo/state/cache-manifest.json`, and enforce cache expiry rules.

#### Scenario: Model download success
- **WHEN** a user supplies a supported model configuration with valid credentials
- **THEN** the downloader retrieves weights and tokenizer files, validates integrity, and persists cache metadata (paths, hashes, expiry) for reuse.

#### Scenario: Cached assets reused offline
- **WHEN** the warmup entrypoint runs with network access disabled and the cache contains unexpired artifacts matching the requested configuration
- **THEN** the downloader skips remote fetches, surfaces a cache-hit event in logs, and the warmup continues without contacting external registries.

#### Scenario: Cache expiry enforced
- **WHEN** cached artifacts exceed their retention window or fail checksum validation
- **THEN** the warmup invalidates the entries, reports the reason, and requires a refreshed download before the build step proceeds.

### Requirement: TensorRT-LLM engine build automation
The warmup sequence SHALL compile the downloaded model into a TensorRT-LLM engine matching the configured GPU precision/context settings, persisting build logs under `llm-demo/logs/<run>/build.log`, engine metadata (version, build flags, hashes) under `llm-demo/state/engine-manifest.json`, and failure diagnostics when compilation errors occur.

#### Scenario: Engine build completes
- **WHEN** the build script runs on a compatible GPU with cached assets available
- **THEN** a TensorRT-LLM engine file is produced, metadata is captured, and failures emit actionable diagnostics linked in the manifest.

### Requirement: Triton serving stack startup
The warmup sequence SHALL launch TensorRT-LLM and Triton services (via scripts or Docker Compose), apply the generated engine, expose configurable HTTP and gRPC endpoints (with optional TLS), expose the `/metrics` endpoint, inject credentials, and block until health probes for both transports succeed or time out while cleaning up partial processes.

#### Scenario: Services become ready
- **WHEN** the launch command executes with valid engine artifacts
- **THEN** TensorRT-LLM and Triton start, HTTP and gRPC health endpoints report ready status, the `/metrics` endpoint responds, and service logs stream to `llm-demo/logs/<run>/triton.log` for operator review.

#### Scenario: Port collision detected
- **WHEN** required ports are already bound or TLS files are missing
- **THEN** the warmup aborts startup, tears down partial processes, and reports the conflict with remediation guidance.

### Requirement: Warmup inference and observability
The warmup sequence SHALL execute scripted inference using default prompts to populate caches, compare responses against golden samples, capture pre- and post-run GPU utilization snapshots via NVML/`nvidia-smi`, and emit JSONL logs per stage (`download.jsonl`, `build.jsonl`, `launch.jsonl`, `inference.jsonl`) plus a metrics summary (`summary.json`) under `llm-demo/logs/<run>/`, capturing success flags and latency p50/p95 values.

#### Scenario: Warmup inference succeeds
- **WHEN** the services report healthy and the warmup driver runs
- **THEN** a test prompt receives a model response, timings populate `summary.json`, GPU utilization snapshots are stored, and structured logs exist for troubleshooting.

#### Scenario: Golden response mismatch
- **WHEN** the model output deviates from the stored golden sample threshold
- **THEN** the warmup flags the deviation, captures the divergent outputs, and surfaces guidance for updating or investigating the golden reference.

### Requirement: Telemetry manifest and retention
The warmup utility SHALL emit an environment manifest summarizing hardware, software versions, artifact hashes, duration metrics, log paths, and retention policies after each run, storing it under `llm-demo/state/<run>-manifest.json` alongside retention metadata controlling log rotation.

#### Scenario: Manifest generated after warmup
- **WHEN** a warmup run completes successfully
- **THEN** a manifest file describing environment, configurations, hashes, GPU snapshots, and timestamps SHALL be written and referenced in documentation.

### Requirement: Conversational chat client with memory and redaction
The warmup utility SHALL include a CLI chat client that connects to the Triton endpoint, maintains rolling conversation memory within a session, enforces rate limits, saves transcripts as JSONL files under `llm-demo/transcripts/<session>.jsonl`, redacts secrets (tokens, API keys, credentials) using configurable patterns, and stores session metadata (model ID, config hash, timestamps).

#### Scenario: Chat session with memory
- **WHEN** an operator starts the chat client and exchanges multiple prompts
- **THEN** each response reflects accumulated conversation context, sanitized transcripts are persisted with metadata, and the session can be ended gracefully while logging a summary entry.

### Requirement: Negative path validation coverage
The warmup solution SHALL include automated or scripted tests that exercise prerequisite failures, checksum mismatches, cache expiry, Triton port collisions, and golden-response deviations, each asserting that the warmup aborts safely and emits the documented diagnostics.

#### Scenario: Failure diagnostics verified
- **WHEN** the negative-path tests run on controlled inputs that trigger each failure mode
- **THEN** the warmup stops before progressing to unsafe stages, writes the expected error artifacts, and returns explicit exit codes for external automation.

### Requirement: Teardown and cleanup guidance
The warmup utility SHALL document and automate shutdown of services, verify process/container termination, confirm GPU memory is released, optionally purge caches per retention policy, and list log/engine directories so operators can reset the environment without residual artifacts.

#### Scenario: Cleanup executed
- **WHEN** the operator runs the provided teardown command or follows documented steps
- **THEN** TensorRT-LLM and Triton processes stop, allocated ports and GPU resources are released, optional cache purges respect policy settings, and a cleanup report is written to `llm-demo/logs/<run>/cleanup.log`.
