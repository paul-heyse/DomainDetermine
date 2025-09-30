## Why
The service layer (FastAPI app, artifact/job endpoints, health/readiness, telemetry, authentication) operates without spec coverage, preventing governance enforcement for Module 7.

## What Changes
- Define service API requirements: artifact CRUD, job submission/status, health/readiness, authentication (JWT/mTLS/RBAC), and observability.
- Scaffold the FastAPI app with handlers, telemetry middleware, and documentation.
- Align CI workflows and readiness checks with the governed service surface.

## Impact
- Affected specs: `service/spec.md`
- Affected code: `src/DomainDetermine/service/{app,handlers,schemas,telemetry}.py`
- Affected docs: `docs/service_layer.md`
- Tests: `tests/test_service_app.py`, `tests/test_cli_app.py`, `tests/test_cli_config.py`, `tests/test_query_service.py`
