## Why
A cold start run of our inference toolchain is currently undocumented and untested. We need a repeatable warmup sequence to download a target LLM, compile it for TensorRT-LLM, launch the Triton backend, and provide a lightweight chat loop so operators can confirm the model responds before integrating it into other modules. The change must spell out hardware/software prerequisites, credential handling, telemetry expectations, cache reuse behavior, dual-protocol health checks, GPU utilization capture, and success gates so the warmup can be executed reliably on approved GPU hosts—even offline after the first run.

## What Changes
- Create an isolated `llm-demo/` utility that owns all warmup scripts, configs, docs, and manifests for spinning up a demo inference stack including environment pre-checks, offline cache reuse, and teardown helpers.
- Automate model artifact retrieval, TensorRT-LLM engine build, and Triton server start commands with HTTP/gRPC health verification, metrics endpoint checks, failure diagnostics, caching/expiry handling, and cleanup safeguards.
- Ship a minimal CLI chat client with rolling conversation memory, rate limiting, sanitized transcript persistence, deterministic response checks, GPU snapshot linkage, and manifest references for audit.
- Capture warmup telemetry (durations, GPU utilization, errors, key paths, environment/version manifest) and provide positive/negative smoke tests to certify both success and failure handling.

## Impact
- Affected specs: llm-demo (new capability)
- Affected code: llm-demo/ (new directory), GPU compatibility checks, credential loaders, cache manager, telemetry/log rotation, offline-mode, negative-path tests, teardown scripts, potential Docker/compose helpers, runtime scripts for TensorRT-LLM and Triton.
