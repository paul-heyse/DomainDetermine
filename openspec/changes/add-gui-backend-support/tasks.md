## 1. Specification & Approval
- [ ] 1.1 Review existing service/governance specs and identify gaps for GUI consumption (API shape, streaming, search, preferences, notifications).
- [ ] 1.2 Align module leads on shared backend requirements and document dependency graph between GUI workspaces and service endpoints.
- [ ] 1.3 Produce API design docs (OpenAPI/GraphQL schemas) and data flow diagrams for approval.

## 2. API & Service Extensions
- [ ] 2.1 Implement REST/GraphQL endpoints for dashboard metrics, artifact lineage, job orchestration, search, and notifications, ensuring schema validation and pagination.
- [ ] 2.2 Add websocket/Server-Sent Event endpoints for job status, notifications, calibration updates, and readiness gates with fallbacks.
- [ ] 2.3 Extend job orchestration service to support GUI-triggered retries, rollbacks, and automation hooks with audit metadata.
- [ ] 2.4 Provide user preference APIs (save views, layouts, filters) with tenancy isolation and policy enforcement.

## 3. Background Services & Infrastructure
- [ ] 3.1 Implement notification/event fan-out pipelines (Redis/Kafka/etc.) to deliver GUI inbox items, alerts, and audit events.
- [ ] 3.2 Build search indexing jobs for artifacts (coverage plans, maps, overlays, prompt packs, readiness reports) with incremental updates and query APIs.
- [ ] 3.3 Enhance telemetry collectors to expose GUI-friendly aggregates (cost, SLA, queue metrics) with caching layers.

## 4. Security, Governance & Compliance
- [ ] 4.1 Enforce RBAC, rate limiting, CSRF protection, and tenant scoping on new endpoints; update governance event logging to capture GUI actions.
- [ ] 4.2 Implement data retention, licensing masking, and audit trails for preference/notification data.
- [ ] 4.3 Update documentation and runbooks for new APIs, search indices, notification pipelines, and operational playbooks.

## 5. Testing & Validation
- [ ] 5.1 Create contract/integration tests for new APIs (REST, GraphQL, websocket) with scenario coverage per module.
- [ ] 5.2 Run load/performance tests simulating GUI usage (dashboard refresh, search, streaming) and optimize caching.
- [ ] 5.3 Execute security testing (penetration, boundary, auth bypass) and ensure logging/tracing coverage.
- [ ] 5.4 Execute `openspec validate add-gui-backend-support --strict`.
