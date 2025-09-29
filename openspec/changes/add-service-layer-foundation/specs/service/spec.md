## ADDED Requirements
### Requirement: Service API Endpoints
The service SHALL expose HTTP endpoints for artifact CRUD, job submission/status, downloads, and health/readiness checks.

#### Scenario: Artifact CRUD
- **WHEN** an operator calls `POST /artifacts` with registry metadata
- **THEN** the service SHALL create the artifact, returning a manifest pointer and emitting structured audit logs.

#### Scenario: Health checks available
- **WHEN** infrastructure probes `GET /healthz` and `GET /readyz`
- **THEN** the service SHALL respond with dependency status (database, queue, object store) and flag slow queries in logs.

### Requirement: API Security & RBAC
The service SHALL require JWT or mTLS authentication, enforcing per-endpoint RBAC aligned to registry roles, and include audit headers (`X-Actor`, `X-Reason`).

#### Scenario: Enforce role-based access
- **WHEN** a client with role `viewer` attempts `DELETE /artifacts/{id}`
- **THEN** the service SHALL reject the request with 403, logging the attempt with audit headers; only `publisher` or `admin` roles may delete.
