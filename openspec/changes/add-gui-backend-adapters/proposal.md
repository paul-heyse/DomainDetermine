## Why

Existing service endpoints expose artifact CRUD and job orchestration but lack GUI-specific adapters such as structured notification feeds, websocket streaming, prompt pack telemetry, and readiness alert fan-out. To power the Python-native NiceGUI front end without duplicating logic, we must extend the service layer with FastAPI-based adapter endpoints that maintain parity with CLI operations and governance audit requirements.

## What Changes

- Introduce FastAPI GUI adapter endpoints (REST/websocket) for notification feeds, job/log streaming, artifact lineage snapshots, readiness waivers, prompt pack readiness telemetry, and automation webhooks.
- Expose command execution endpoints that wrap existing OperationExecutor flows with dry-run support, audit headers, CLI parity, and typed error responses for GUI clients.
- Provide governance event bridge APIs for acknowledgement/snooze workflows, readiness waiver submission, release manifest promotion, and manifest hash verification using Python services.
- Add service-side caching, rate limiting, feature flags, and cost telemetry to support multi-tenant GUI consumption without impacting existing CLI paths.
- Emit GUI-specific observability signals (OpenTelemetry spans, structured logs) tailored to the Python GUI stack and incident workflows.

## Impact

- Affected specs: `service`, `governance`, `readiness`, `prompt-pack`, `gui` capability.
- Affected code: FastAPI routers/websocket handlers, OperationExecutor wrappers, governance event bridge modules, telemetry instrumentation, documentation for Python GUI consumers.
