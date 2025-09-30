## ADDED Requirements
### Requirement: Service Job Orchestration
The service SHALL provide asynchronous job submission, status polling, retry policies, and log retrieval for long-running operations tagged by tenant/project.

#### Scenario: Submit plan build job
- **WHEN** a client posts to `POST /jobs` with job type `plan-build`
- **THEN** the service SHALL enqueue the job with tenant/project tags, return a job ID, and allow polling via `GET /jobs/{id}` including retry counts and log pointers.

#### Scenario: Retrieve job logs
- **WHEN** an operator requests `GET /jobs/{id}/logs`
- **THEN** the service SHALL stream logs associated with the job, masking sensitive data and indicating completion status.

### Requirement: Quotas and Rate Limits
The service SHALL enforce per-tenant compute and cost quotas, applying rate limits with informative error responses.

#### Scenario: Enforce tenant quota
- **WHEN** a tenant exceeds its daily plan-build quota
- **THEN** the service SHALL reject new submissions with a 429 error including `Retry-After` metadata and quota usage details.

### Requirement: Service Observability
The service SHALL emit OpenTelemetry traces and metrics for API requests and job execution, including SPARQL/cache metrics surfaced via `/metrics` or logging endpoints.

#### Scenario: Trace job lifecycle
- **WHEN** a job runs through the queue
- **THEN** the service SHALL produce traces capturing enqueue, worker execution, external calls (SPARQL, registry), and completion, publishing metrics for latency, cache hit ratios, and errors.
