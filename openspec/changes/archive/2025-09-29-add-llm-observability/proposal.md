## Why
Operating the local Qwen3 Triton stack requires strong observability: latency, queueing, KV reuse, speculation acceptance ratios, and integration with the governance registry. We also need incident procedures, SLO dashboards, and backup/restore for engine artifacts.

## What Changes
- Define telemetry collection (return_perf_metrics, structured logs) and dashboards for latency, queue delay, utilization, KV reuse, and speculation acceptance.
- Connect LLM events (engine publishes, warm-ups, rollbacks) into the governance event log and backup manifests.
- Document incident response, rollback, and capacity planning playbooks for the RTX 5090 deployment.

## Impact
- Affected specs: llm-runtime, governance
- Affected code: observability pipeline, governance event log integration, runbooks
