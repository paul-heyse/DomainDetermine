## Why
LLM observability (perf metrics, token accounting, guided decoding instrumentation) needs canonical requirements to ensure Module 6 integrates with readiness dashboards.

## What Changes
- Specify metrics/log schema, telemetry pipelines, alert thresholds, and governance integration for LLM operations.
- Implement/confirm observability tooling in `src/DomainDetermine/llm/observability.py` and provider logging.
- Document dashboards and alert policies.

## Impact
- Affected specs: `llm-runtime/spec.md`, `readiness/spec.md`
- Affected code: `src/DomainDetermine/llm/observability.py`, `src/DomainDetermine/llm/provider.py`
- Affected docs: `docs/llm_observability.md`, readiness docs
- Tests: Observability unit tests
