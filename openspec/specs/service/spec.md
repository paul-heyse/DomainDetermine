## Purpose
Provide an automation-ready HTTP interface for managing artifacts and asynchronous jobs while delivering observability, health, and security controls consistent with the registry and RBAC policies.
## Requirements
### Requirement: Artifact CRUD Operations
The service SHALL expose REST endpoints to create, list, update, and delete registry artifacts, returning structured manifests and audit logs for each operation.

#### Scenario: Create artifact via POST
- **WHEN** a client issues `POST /artifacts` with artifact metadata
- **THEN** the service SHALL persist the artifact, return its identifier and manifest pointer, and log the actor/action using `X-Actor` and `X-Reason` headers.

#### Scenario: Delete artifact enforces RBAC
- **WHEN** a client lacking `admin` or `publisher` role calls `DELETE /artifacts/{id}`
- **THEN** the service SHALL respond with HTTP 403, logging the unauthorized attempt, and no artifact SHALL be removed.

### Requirement: Job Submission and Monitoring
The service SHALL provide endpoints for enqueuing jobs, checking status, streaming logs, and reporting quota usage per tenant/job type.

#### Scenario: Submit job within quota
- **WHEN** a tenant submits `POST /jobs` for a job type under its quota limit
- **THEN** the service SHALL accept the request with HTTP 202 and return a job record with status `queued`.

#### Scenario: Quota exceeded rejects job
- **WHEN** a tenant exceeds its quota for a job type
- **THEN** the service SHALL reject additional `POST /jobs` requests with HTTP 429 and include quota usage details in the response body and logs.

### Requirement: Artifact Downloads and Log Streaming
The service SHALL allow clients to stream artifact payloads or job logs via dedicated endpoints while respecting RBAC and audit headers.

#### Scenario: Stream job logs
- **WHEN** a client with viewer access calls `GET /jobs/{id}/logs`
- **THEN** the service SHALL stream plain-text logs for the job and log the access event with actor and reason metadata.

### Requirement: Health and Readiness Probes
The service SHALL expose `/healthz` and `/readyz` endpoints that report dependency status (database, queue, object store) and surface slow-query warnings for observability.

#### Scenario: Health check response
- **WHEN** infrastructure probes `/healthz`
- **THEN** the service SHALL respond with HTTP 200 and a payload containing overall status plus dependency state and any slow-query diagnostics.

### Requirement: API Security and RBAC
The service SHALL require JWT or mTLS authentication, enforce per-endpoint role checks aligned to registry roles, and propagate audit headers (`X-Actor`, `X-Roles`, `X-Tenant`, `X-Reason`).

#### Scenario: Enforce role-based access
- **WHEN** a caller authenticated with role `viewer` attempts a privileged operation (e.g., `DELETE /artifacts/{id}`)
- **THEN** the service SHALL return HTTP 403, record the denied attempt with audit headers, and keep artifacts unchanged.

#### Scenario: Missing authentication headers rejected
- **WHEN** a request omits required audit/authentication headers
- **THEN** the service SHALL return HTTP 401 and not execute the requested operation.

### Requirement: Service Observability
The service SHALL emit OpenTelemetry traces and metrics for API requests and job execution, including cache/SPARQL latency where applicable.

#### Scenario: Trace job lifecycle
- **WHEN** a job transitions from enqueue to completion
- **THEN** the service SHALL produce spans capturing queue entry, handler execution, external calls, and completion metadata (tenant, project, job type).

#### Scenario: Record API metrics
- **WHEN** any HTTP request is processed
- **THEN** the service SHALL increment request counters and record latency metrics tagged by route and status code, exposing them through the telemetry pipeline.

### Requirement: Service API Surface
The service SHALL expose REST endpoints for artifact CRUD (`/artifacts`), job submission/status (`/jobs`), and auxiliary registry interactions. Endpoints SHALL enforce JSON payload schemas, return typed error codes, and integrate with governance manifests.

#### Scenario: Artifact creation
- **WHEN** a client POSTs to `/artifacts`
- **THEN** the service SHALL validate the payload, persist it via the governance registry, return the artifact ID, and log the operation with trace ID.

### Requirement: Authentication & Authorization
The service SHALL support JWT and/or mTLS authentication, enforcing RBAC aligned with registry roles (reader, publisher, operator). Unauthorized requests SHALL return 401/403 with audit logging.

#### Scenario: Role enforcement
- **WHEN** a user without publisher role attempts to publish an artifact
- **THEN** the service SHALL reject the request with 403 and log the access attempt.

### Requirement: Health & Readiness Endpoints
The service SHALL provide `/healthz` (process health), `/readyz` (dependency checks), and `/livez` (liveness) endpoints. Readiness SHALL verify registry connectivity, job runner state, and configuration integrity.

#### Scenario: Readiness failure surfaced
- **WHEN** the registry is unreachable
- **THEN** `/readyz` SHALL return 503 with a descriptive payload and trigger readiness alerts.

### Requirement: Observability & Telemetry
All requests SHALL be wrapped with telemetry middleware capturing request counts, latency, status codes, and trace IDs. Background jobs SHALL emit spans via `job_span` utilities and log success/failure outcomes with retries.

#### Scenario: Telemetry recorded
- **WHEN** a request completes
- **THEN** the middleware SHALL record metrics and traces with attributes (`http.method`, `route`, `tenant`, `status`) for observability pipelines.

