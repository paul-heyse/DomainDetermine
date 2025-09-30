## 1. Specification & Approval

- [x] 1.1 Document service endpoints, auth requirements, telemetry, and health/readiness expectations in the spec.
- [x] 1.2 Review with Module 7 owners.

## 2. Implementation

- [x] 2.1 Scaffold FastAPI app with Uvicorn settings and base routing.
- [x] 2.2 Implement artifact CRUD, job submission/status endpoints, and integrate job runner stubs.
- [x] 2.3 Add health/readiness endpoints, telemetry middleware, and slow-query warnings.
- [x] 2.4 Implement JWT/mTLS auth and RBAC aligned to registry roles.

## 3. Documentation & CI

- [x] 3.1 Update `docs/service_layer.md` with API usage, auth, telemetry, and deployment guidance.
- [x] 3.2 Update CI workflows to exercise service readiness endpoints.

## 4. Testing & Validation

- [x] 4.1 Expand service-layer pytest coverage.
- [x] 4.2 Run `pytest -q tests/test_service_app.py tests/test_cli_app.py tests/test_cli_config.py tests/test_query_service.py`.
- [x] 4.3 Execute `openspec validate add-service-layer-foundation --strict`.
