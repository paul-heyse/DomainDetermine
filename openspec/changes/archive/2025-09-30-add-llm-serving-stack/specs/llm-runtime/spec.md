## ADDED Requirements
### Requirement: Engine Build Workflow
LLM deployment SHALL produce TensorRT-LLM engines using a governed build pipeline (`trtllm-build`) that records model ID, quantisation mode, tokenizer snapshot, engine hash, and build environment (container image, CUDA/cuDNN versions). Build manifests SHALL be stored alongside engines.

#### Scenario: Build manifest generated
- **WHEN** an engine is built
- **THEN** the pipeline SHALL produce `engine-manifest.json` capturing input model hash, quantisation config, build timestamp, container digests, and deployment target.

### Requirement: Triton Repository Layout
Serving SHALL use a Triton model repository with versioned subdirectories (`models/<model_name>/<version>/model.plan`, config files). Each version SHALL include `config.pbtxt` reflecting runtime constraints (max batch size, tensor parallelism, guided decoding). Only approved versions SHALL be symlinked for production.

#### Scenario: Repository validation
- **WHEN** the deployment pipeline syncs the Triton repository
- **THEN** it SHALL validate repository structure and config fields, failing deployment if required parameters are missing.

### Requirement: Deployment & Rollback Procedures
Serving SHALL provide scripted deployment (`serve_triton.sh`) and rollback workflows that rollout new engines via canary, monitor readiness probes, and revert using previous engine version upon failure. Rollbacks SHALL be logged in governance events.

#### Scenario: Canary rollout
- **WHEN** a new engine is deployed
- **THEN** the deployment script SHALL start a canary instance, run smoke tests, and only promote the engine to production if checks pass within defined SLAs.

### Requirement: Capacity Planning & Observability
Serving SHALL document capacity assumptions (GPU type, concurrent request limits, memory footprint) and expose metrics (queue delay, tokens in/out, failure rate, GPU utilization) to readiness dashboards. Exceeding capacity thresholds SHALL trigger alerts.

#### Scenario: Capacity alert
- **WHEN** queue delay exceeds the governed threshold for five minutes
- **THEN** the system SHALL alert the LLM operations channel and suggest scaling actions or rollback.
