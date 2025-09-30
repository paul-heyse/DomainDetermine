## 1. Specification & Approval

- [ ] 1.1 Review GUI architecture/foundation/operations specs to capture required adapter endpoints (commands, notifications, lineage, readiness, prompt pack metrics, automation hooks, incident feeds).
- [ ] 1.2 Align service owners, governance, readiness, security, and operations on API surface, authentication, rate limiting, feature flag, residency, and idempotency policies.
- [ ] 1.3 Produce API contracts (OpenAPI/GraphQL, websocket schema) and event flow diagrams for approval; circulate CLI parity/migration plan.

## 2. API & Event Design

- [ ] 2.1 Design REST/websocket/search schemas for GUI command execution, notification feeds, lineage snapshots, readiness waivers/attestations, prompt pack telemetry, incident alerts, and automation triggers including error conventions.
- [ ] 2.2 Define audit header propagation, OperationExecutor integration, CLI parity behaviors, idempotency key strategy, and rollback semantics.
- [ ] 2.3 Specify caching strategies, rate limits, streaming/replay/backoff policies, feature flag enforcement, and data residency routing per tenant.
- [ ] 2.4 Publish API reference (`docs/gui/backend_adapters_api.md`) covering schemas, auth requirements, idempotency usage, CLI parity guidance, and troubleshooting matrix.

## 3. Implementation

- [ ] 3.1 Implement `/gui/commands/*` endpoints wrapping OperationExecutor flows with dry-run support, CLI parity, telemetry, and governance hooks.
- [ ] 3.2 Build websocket notification hub with acknowledgement/snooze, assignment, backpressure handling, and audit persistence.
- [ ] 3.3 Add lineage snapshot and prompt pack metrics endpoints with manifest verification, diff snapshots, and search indexing integration.
- [ ] 3.4 Implement readiness waiver bridge, governance event propagation, automation webhook endpoints, and CLI parity tests.
- [ ] 3.5 Deliver command history APIs and export features for audit/compliance.
- [ ] 3.6 Publish developer documentation (`docs/gui/backend_adapters.md`) detailing adapters, notification cursors, and integration examples.

## 4. Observability, Security & Compliance

- [ ] 4.1 Instrument endpoints with OpenTelemetry spans, structured logs, and metrics tagged by tenant/actor/command; integrate with incident dashboards.
- [ ] 4.2 Configure RBAC, rate limits, throttling responses, CSRF, replay protection, and feature flag checks for adapter endpoints.
- [ ] 4.3 Conduct security review covering authN/Z, input validation, secret handling, and audit policy updates.
- [ ] 4.4 Document runbooks for notification/event pipeline operations, alert responses, and data residency audits.

## 5. Testing & Validation

- [ ] 5.1 Create contract/integration tests using GUI client stubs for commands, notifications, lineage, and waiver APIs.
- [ ] 5.2 Validate OperationExecutor parity by comparing CLI vs GUI executions (artifacts, telemetry, error handling) across modules.
- [ ] 5.3 Run load/performance tests for streaming endpoints and caching strategies, verifying backpressure/backoff behavior.
- [ ] 5.4 Execute security/penetration tests for adapter APIs and confirm audit trails.
- [ ] 5.5 Exercise websocket reconnect, acknowledgement, snooze, and replay flows in staging.
- [ ] 5.6 Execute `openspec validate add-gui-backend-adapters --strict`.
