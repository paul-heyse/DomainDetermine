## Why
The service layer needs an async job system with quotas and telemetry so long-running operations (plan builds, eval runs) can be tracked, retried, and rate limited per tenant.

## What Changes
- Extend service specs to cover job orchestration (queues, status polling, logs) and per-tenant quotas/rate limits.
- Enhance observability requirements with OpenTelemetry traces and SPARQL/cache metrics surfaced via the service.

## Impact
- Affected specs: `service/jobs`, `service/quotas`, `observability/telemetry`
- Affected code: Job orchestrator (Celery/RQ/Prefect), quota manager, telemetry pipelines
