## Why
Operators require an automation-friendly API to manage artifacts, submit jobs, and download outputs. No dedicated FastAPI service exists to expose registry operations, health endpoints, or secure RBAC.

## What Changes
- Introduce a service/API capability spec covering artifact CRUD, job submission/status, artifact download, and health/readiness endpoints.
- Add security/RBAC requirements for JWT/mTLS authentication, per-endpoint role checks, and audit headers.

## Impact
- Affected specs: `service/api`, `security/rbac`
- Affected code: FastAPI service, auth middleware, health checks
