# add-gui-backend-support – Design

## Context

The GUI requires backend extensions beyond the dedicated adapters: shared dashboard metrics, search indexing, preferences, notification fan-out, and telemetry aggregation. This change upgrades core services so the GUI architecture, foundation, and operations layers can rely on consistent REST/websocket/GraphQL APIs without duplicating logic. All work remains in Python (FastAPI, Pydantic, Redis/DuckDB workers) to align with existing infrastructure.

## Goals

- Provide unified API endpoints for dashboards, artifact lineage, search, job orchestration, notifications, and preferences.
- Introduce streaming (websocket/SSE) channels for job status, alerts, readiness, and prompt pack updates with graceful fallbacks.
- Enhance background services for notification fan-out, search indexing, and telemetry aggregation.
- Ensure RBAC, rate limiting, tenant isolation, and audit logging across new endpoints.
- Document operational runbooks, testing strategy, and observability requirements.

## Non-Goals

- Implement GUI components (handled by add-gui-* changes).
- Replace existing CLI workflows; all APIs must maintain parity.
- Provide external ticketing connectors (covered later in operations change).

## API Surface

| Category | Endpoint(s) | Description |
| --- | --- | --- |
| Dashboard metrics | `GET /service/gui/dashboard`, `GET /service/gui/metrics/{module}` | Aggregated ingestion, coverage, mapping, overlay, readiness, prompt pack, governance, cost metrics; supports filters (tenant, time range). |
| Artifact lineage | `GET /service/gui/artifacts/{id}/lineage`, `GET /service/gui/artifacts/search` | Consolidates metadata, upstream/downstream links, diff hashes, licensing notes, search with pagination/sorting. |
| Job orchestration | `POST /service/gui/jobs/{verb}`, `PATCH /service/gui/jobs/{id}/retry`, `PATCH /service/gui/jobs/{id}/cancel` | Trigger/retry/cancel operations; record audit metadata and automation hooks. |
| Notifications | `GET /service/gui/notifications`, `WS /service/gui/notifications/{tenant}` | Initial inbox fetch + live updates (ack, snooze, assign). Fallback SSE endpoint provided. |
| Preferences | `GET/PUT /service/gui/preferences`, `POST /service/gui/preferences/views` | Store user/tenant preferences (theme, saved views, filters) with policy enforcement and audit trail. |
| Search | `GET /service/gui/search` | Federated search across artifacts (coverage/mapping/overlay/readiness/prompt packs) returning relevance scores, highlights, governance metadata. |

## Streaming Channels

- `/service/gui/ws/jobs/{tenant}` – job status updates, progress, runtime metrics.
- `/service/gui/ws/notifications/{tenant}` – governance/readiness/prompt pack/cost alerts with ack semantics.
- `/service/gui/ws/readiness/{tenant}` – gate statuses, waivers, snooze updates.
- `/service/gui/ws/prompt-pack/{tenant}` – calibration status, constraint adherence.
- Each channel built with `fastapi-websocket-pubsub` + Redis Streams for replay; SSE fallback provided via chunked responses for clients without websocket support.

## Background Services

- **Notification fan-out**: Redis Streams + worker (`gui.notifications.publisher`) reading governance, readiness, cost, incident topics, transforming to GUI payload schema, enforcing tenant filters.
- **Search indexing**: Celery/Prefect job `gui.search.indexer` ingesting artifacts into DuckDB/Elastic index; incremental updates triggered by governance events; supports multi-tenant partitions.
- **Telemetry aggregation**: Periodic jobs computing cost, SLA, queue metrics; results cached in Redis with TTL for dashboard queries.

## Security & Compliance

- RBAC enforced via FastAPI dependencies; scopes like `gui:dashboard`, `gui:search`, `gui:notifications`. Feature flags enforced per tenant.
- Rate limiting using `slowapi` or custom middleware (e.g., 100 req/min per tenant for dashboards, 20 req/min for job commands).
- Audit logging: every mutation logs actor, tenant, endpoint, payload hash, status, latency, trace id.
- Data residency: endpoints route to region-specific data stores (EU vs US). Notification fan-out ensures events stay within region boundaries.
- Licensing: lineage/search responses mask restricted fields; include license tag indicating restrictions.
- Retention: notifications and preferences stored with TTL/archival jobs; logs retained per compliance policy.

## Observability

- OpenTelemetry spans for REST/websocket endpoints; trace propagation from OperationExecutor.
- Metrics: request counts, latency, error rates, cache hit rate, stream backlog, search query performance.
- Dashboards (Grafana) monitoring: success/failure rates, fan-out lag, job queue length, SSE/websocket connection counts.
- Alerts based on backlog thresholds, error spikes, rate-limit breaches, residency anomalies.

## Testing Strategy

- Contract tests per endpoint verifying schemas, pagination, RBAC failures, rate limits, feature flag gating.
- Streaming tests for websocket/SSE reconnection and replay using integration harness.
- Search tests verifying filters, ranking, highlight accuracy using fixtures.
- Performance tests for dashboard endpoints (load 100 concurrent sessions) and notification streams (simulate 10k events/hr).
- Security tests: CSRF, auth bypass, cross-tenant access, replay attacks, rate-limit evasion.

## Runbooks & Docs

- `docs/gui/backend_support_runbook.md`: setup, deployment, scaling instructions, incident response.
- `docs/gui/backend_support_api.md`: endpoint catalog, schemas, auth, error codes.
- On-call checklist for notification fan-out and search indexing.

## Deliverables

- FastAPI routers (`DomainDetermine.service.gui_*` modules) implementing endpoints and websockets.
- Background workers for notifications, search, telemetry.
- Redis/DuckDB schema updates (migration scripts).
- Automated tests (`tests/gui_backend_support/*`).
- Documentation updates + runbooks.

## Risks & Mitigations

- **Streaming overload**: apply backpressure, partition streams by tenant, support SSE fallback.
- **Search drift**: schedule periodic reindexing, diff index vs. source counts.
- **Multi-region complexity**: use region-specific secrets/config; test residency compliance regularly.
- **Preference conflicts**: apply policy enforcement, allow admins to reset preferences.
