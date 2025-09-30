## ADDED Requirements
### Requirement: Job Lifecycle Management
The service SHALL provide job submission, status, retry, and cancellation APIs. Jobs SHALL record type, payload, tenant, project, actor, reason, timestamps, retry count, and log pointer. Job state transitions SHALL be persisted via the governance registry.

#### Scenario: Job submission recorded
- **WHEN** a client submits a job
- **THEN** the service SHALL persist a `JobRecord` with status `queued`, enqueue it via the runner, and return the job ID.

### Requirement: Quota Enforcement
The service SHALL enforce per-tenant quotas (e.g., max concurrent jobs, daily compute budget) before enqueuing jobs. Quota breaches SHALL raise a structured error with retry-after guidance and emit alerts.

#### Scenario: Quota exceeded
- **WHEN** job submission would exceed the tenant’s quota
- **THEN** the service SHALL reject the request with `QuotaExceededError`, include `retry_after_seconds`, and emit a governance event.

### Requirement: Telemetry & Logging
Job execution SHALL emit spans (`job_span`), metrics (queue depth, job age, retries, duration), and structured logs containing job ID, status transitions, handler name, and errors. Telemetry SHALL integrate with readiness dashboards.

#### Scenario: Telemetry emitted on completion
- **WHEN** a job completes or fails
- **THEN** the runner SHALL update metrics and logs, recording duration, retries, and log pointer.

#### Scenario: Governance events recorded
- **WHEN** jobs are enqueued, completed, or fail/quota is exceeded
- **THEN** the service SHALL append governance events (`service_job_*`) with tenant, job type, retries, and log pointer for audit.
