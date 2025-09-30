# Service Layer API

The service layer exposes a FastAPI application (`DomainDetermine.service.app:create_app`) that fronts artifact registry actions and asynchronous job orchestration. It is designed for automation scenarios where operators or CI pipelines need HTTP access instead of the CLI.

## Running the service

```bash
uvicorn DomainDetermine.service.app:create_app --factory --reload
```

The factory expects a `JobManager` instance. For local development the in-memory registry (`InMemoryRegistry`) can be used:

```python
from DomainDetermine.service import InMemoryRegistry, JobManager, create_app

registry = InMemoryRegistry()
app = create_app(JobManager(registry))
```

## Authentication & Headers

All requests must include the following headers (stubbed in tests; wire to JWT/mTLS in production):

- `X-Actor` – human or service principal identifier.
- `X-Roles` – comma-separated roles (`admin`, `publisher`, `viewer`).
- `X-Tenant` – tenant identifier used for quota enforcement.
- `X-Reason` – optional audit note (defaults to `unspecified`).

Requests missing mandatory headers receive HTTP 401; callers without required roles receive HTTP 403. Privileged endpoints (`POST/PUT/DELETE /artifacts`) require `admin` or `publisher`; read/queue endpoints accept `viewer`.

## REST Endpoints

### `/healthz` and `/readyz`

Return JSON payloads with overall status, dependency checks, and slow-query warnings. The readiness endpoint reports the current job queue depth and flips to `not-ready` whenever slow-request telemetry exceeds the configured threshold, allowing CI/CD gates to block on degraded performance. Intended for Kubernetes probes and GitHub Actions readiness jobs.

### `/artifacts`

- `POST /artifacts` – create an artifact. Body matches `ArtifactCreateRequest` (`name`, `type`, `metadata`, optional `content`, `content_type`). Returns manifest pointer and indicates whether download content is available.
- `GET /artifacts` – list artifacts visible to the caller.
- `PUT /artifacts/{id}` – update metadata and optionally replace inline content.
- `DELETE /artifacts/{id}` – remove an artifact (requires `publisher`/`admin`).

### `/artifacts/{id}/download`

Stream artifact content. Inline payloads are stored as bytes in the registry; production deployments can swap in an object store implementation.

### `/jobs`

- `POST /jobs` – enqueue a job (payload + job_type + tenant/project). Enforces quotas and returns HTTP 202 with job record.
- `GET /jobs` – list jobs for the current tenant.
- `GET /jobs/{id}` – fetch status.
- `GET /jobs/{id}/logs` – stream plain-text logs.
- `GET /quotas` – return quota limits/usage for the tenant.

Quota violations raise HTTP 429 and include current usage in the response body.

### Job execution

`JobManager` coordinates queueing with a threaded runner (`ThreadedJobRunner`). Handlers can be registered per job type:

```python
def build_plan(record, manager):
    # long-running work here
    return f"s3://logs/{record.job_id}"

job_manager.register_handler("plan-build", build_plan)
```

Handlers are executed in background worker threads; failures trigger automatic retries (default `max_retries=1`) and ultimately mark the job as `failed` when the retry budget is exhausted. Tenants, projects, and actors are preserved in the `JobRequest` for audit.

Out of the box the service registers lightweight handlers for `plan-build`, `eval-run`, and `audit-report` jobs, emitting structured JSON log lines that include tenant, project, and job identifiers. Swap or extend them by calling `register_handler` before serving traffic.

### Governance events & alerts

- Job lifecycle events are written to the governance event log (`service_job_enqueued`, `service_job_completed`, `service_job_failed`, `service_job_quota_exceeded`). Integrate by passing a `GovernanceEventLog` into `create_app`.
- Quota violations log warnings (`DomainDetermine.service.jobs`) that can be routed to alerting (e.g., OpsGenie).
- Event payloads include job type, tenant, project, retries, and log pointers so governance reviews can trace job history.
- Metrics: export queue depth, job duration, retry count, and quota usage to the shared observability stack (`service_job_duration_ms`, `service_job_queue_depth`, `service_job_quota_usage`). Dashboards should surface per-tenant quota consumption with thresholds (`>=80%` warn, `>=100%` page) and link to the corresponding governance events.

## Observability

FastAPI middleware should populate structured logs with audit headers. A `SlowRequestTracker` buffers the most recent slow requests so they surface via `/healthz` and `/readyz`, making it easy to push alerts or block deploys when latency spikes. Add Prometheus exporters or OTEL instrumentation as follow-up work.

The service ships with an optional OpenTelemetry middleware (`TelemetryMiddleware`) that records request counters and latency histograms when OTEL is installed. Job execution spans are emitted around handler execution (`job.execute`) and enqueue operations, capturing tenant, project, and job type attributes. Metrics or spans are no-ops when OTEL libraries are unavailable. Slow requests automatically emit instrumentation hooks that can be forwarded to dashboards.

## Integration Pattern

- Use CLI or automation to publish artifacts; the service ensures registry consistency.
- Invoke `/jobs` for long-running tasks (plan builds, audits). Poll `/jobs/{id}` or subscribe to logs via `/jobs/{id}/logs`.
- CI pipelines can gate deploys on `/readyz`.

Further extensions: swap `InMemoryRegistry` with the production registry client, integrate JWT validation, and connect to async workers for job execution.
