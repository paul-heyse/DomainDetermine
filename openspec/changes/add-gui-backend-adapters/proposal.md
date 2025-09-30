## Why

Existing service endpoints expose artifact CRUD and job orchestration but lack GUI-oriented capabilities such as structured notification feeds, websocket streaming, prompt pack telemetry adapters, readiness alert fan-out, and incident/retention tooling. To deliver the new GUI workspaces without duplicating logic, we must extend the service layer with GUI-focused contracts that maintain parity with CLI operations and governance audit requirements.

## What Changes

- Introduce GUI adapter endpoints (REST/websocket/search) for notification feeds, job/log streaming, lineage snapshots, prompt pack readiness telemetry, readiness waivers, incident events, and automation hooks.
- Expose command execution endpoints that wrap existing OperationExecutor flows with dry-run support, idempotency, audit headers, and typed error responses for GUI clients.
- Provide governance event bridge APIs for acknowledgement/snooze workflows, readiness attestation, manifest hash verification, release promotion, and retention policy execution.
- Add service-side caching, rate limiting, feature-flag gating, and residency-aware routing to support multi-tenant GUI consumption without impacting existing CLI paths.
- Emit GUI-specific observability signals (OpenTelemetry spans, structured logs) aligned with notification acknowledgement, incident workflows, and retention automation.

## Impact

- Affected specs: `service`, `governance`, `readiness`, `prompt-pack`, `gui` capability.
- Affected code: new adapter endpoints/websocket handlers, OperationExecutor wrappers, governance event bridge, incident streams, telemetry instrumentation, documentation for GUI consumers.
