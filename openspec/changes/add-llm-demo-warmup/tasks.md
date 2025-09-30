## 1. Planning & prerequisites
- [x] 1.1 Author `llm-demo/docs/prerequisites.md` and `llm-demo/config/prerequisites.yaml` detailing supported GPUs, driver/toolkit versions, container images, env vars, disk-space requirements, and credential expectations.
- [x] 1.2 Implement a preflight validator that ingests the prerequisites config, checks the host environment, and writes `llm-demo/state/prereq-manifest.json` with pass/fail status and remediation guidance.

## 2. Configuration & warmup automation
- [x] 2.1 Define the typed schema for `llm-demo/config/model.yaml` plus CLI overrides, including model/tokenizer IDs, precision profile, TensorRT-LLM build parameters, credential sources, cache retention rules, and offline-mode flag.
- [x] 2.2 Build the downloader that applies the schema, fetches model/tokenizer assets, verifies checksums, records results in `llm-demo/state/cache-manifest.json`, and reports explicit cache-hit/cache-expiry events.
- [x] 2.3 Implement the TensorRT-LLM engine build script that emits structured logs to `llm-demo/logs/<run>/build.log` and engine metadata to `llm-demo/state/engine-manifest.json`.
- [x] 2.4 Create launch automation (scripts or Docker Compose) that starts TensorRT-LLM/Triton, streams logs to `llm-demo/logs/<run>/triton.log`, exposes configured HTTP/gRPC endpoints plus `/metrics`, and tears down partial processes on failure or port collision.
- [x] 2.5 Provide a warmup driver that executes scripted inference(s), captures GPU utilization snapshots before/after, generates golden-response comparisons, and writes staged JSONL logs plus `summary.json` under `llm-demo/logs/<run>/`.
- [x] 2.6 Add a cache-reuse smoke path that runs with network disabled to confirm repeated warmups succeed offline.

## 3. Chat interface & observability
- [x] 3.1 Build the CLI chat client with rolling memory, rate limiting, configurable endpoint selection, and TLS support.
- [x] 3.2 Persist sanitized transcripts and session metadata as JSONL under `llm-demo/transcripts/<session>.jsonl`, implementing secret redaction patterns and linking to run manifests.
- [x] 3.3 Emit structured telemetry manifests for each run (`llm-demo/state/<run>-manifest.json`) summarizing environment versions, artifact hashes, GPU snapshots, durations, and retention policies.

## 4. Validation & documentation
- [x] 4.1 Write positive smoke tests or scripts that execute the full warmup on supported hardware and assert log/manifest artifacts exist with expected schemas.
- [x] 4.2 Add negative-path tests covering prerequisite failures, checksum mismatch, cache expiry, Triton port collision, and golden-response deviation, verifying diagnostics and exit codes.
- [x] 4.3 Document usage, offline-mode, teardown, cleanup, and retention workflows in `llm-demo/README.md`, referencing log locations, metrics endpoints, and troubleshooting steps.
- [x] 4.4 Add operator guidance for interpreting metrics, GPU snapshots, transcripts, and manifests, including data-retention and sanitization expectations.
