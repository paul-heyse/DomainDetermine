## ADDED Requirements
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
