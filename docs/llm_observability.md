# LLM Observability & Incident Response

This runbook covers telemetry collection, governance integration, and incident response for the Qwen3-32B Triton stack.

## Metrics & Logs

- Triton `return_perf_metrics` captures latency, queue delay, token counts, KV reuse stats, and speculative acceptance.
- Provider logs emit JSON with fields:
  - `duration_ms`, `queue_delay_us`
  - `tokens_in`, `tokens_out`
  - `kv_cache_reuse` (hits/misses)
  - `speculative` (attempts/accepts)
  - `schema_id`, `engine_hash`, `quantisation`
  - `cost_usd`, `queue_delay_budget_overrun`, `token_budget_overrun`
  - `error_code`, `warning`

## Dashboards / SLOs

| SLO | Threshold | Alert Condition |
| --- | --- | --- |
| P95 latency | < 800 ms | Breached for 5m |
| Queue delay | < 1500 µs | Breached for 5m |
| KV reuse ratio | > 0.4 | < 0.4 for 10m |
| Speculative accept ratio (if enabled) | > 0.6 | < 0.6 for 15m |
| Token budget | < governed limit | Trigger when `token_budget_overrun=true` for 5m |
| Cost per request | < `$max_cost_usd` | Trigger when `cost_usd` exceeds threshold |

## Governance Events

- `llm_engine_published`: engine hash + manifest recorded.
- `llm_warmup_completed` / `llm_warmup_failed`: warm-up success/failure with schema versions.
- `llm_rollback_completed`: references restored manifest and actor.
- `llm_observability_alert`: emitted when cost or queue delay thresholds breach readiness policy.

## Backups

Artifacts included:

- Engine plan files
- Tokenizer info JSON and tokenizer directory
- Schema registry files (`llm/schemas`)
- Triton `config.pbtxt`

Backups use `BackupCoordinator.record_backup` with artifact list and verification hash; store in object storage destinations per replication targets.

## Incident Response

1. Acknowledge alert and review latest metrics snapshot.
2. Inspect governance event log for recent warm-up failures or rollbacks.
3. Run warm-up scripts; if warm-up fails, traffic stays off until fixed.
4. If regression confirmed, follow rollback instructions in `docs/llm_serving_stack.md`.
5. File incident report and update governance log with `llm_rollback_completed` event.
6. For cost overruns, notify finance via readiness webhook and capture waiver if spend is accepted.

## Capacity Planning

- Maintain ≥ 25% VRAM headroom; monitor tokens_in/out to infer KV usage.
- Adjust `max_queue_delay_microseconds` and batch size to balance latency vs throughput.
- Speculation toggles off by default; enable for long-form workloads only after calibrating acceptance ratio.
