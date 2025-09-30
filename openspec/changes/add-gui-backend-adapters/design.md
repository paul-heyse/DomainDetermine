# add-gui-backend-adapters – Design

## Context

The GUI will rely on FastAPI adapters that mirror CLI OperationExecutor behavior while supporting realtime notifications, lineage, readiness, and prompt pack telemetry. This design translates the requirements in `specs/gui/spec.md` and `specs/service/spec.md` into concrete API groups, data models, authentication policies, and observability baselines.

## Goals

- Deliver `/gui/commands/*` endpoints wrapping existing OperationExecutor commands with CLI parity (dry-run, audit headers, idempotency keys) exposed to the GUI under `src/DomainDetermine/gui`.
- Provide websocket notification feeds for governance, readiness, incident, prompt pack, and cost events with acknowledgement/snooze semantics.
- Expose lineage/prompt metrics/search APIs optimized for GUI usage.
- Bridge readiness waivers and attestations, ensuring governance event propagation.
- Instrument endpoints with OpenTelemetry, rate limiting, and security checks suited for multi-tenant GUI consumption.

## API Surface Overview

| Adapter | Endpoints | Description |
| --- | --- | --- |
| Command execution | `POST /gui/commands/{verb}` (ingest, plan, audit, evalgen, run, publish, readiness) | Wrap OperationExecutor flows; support dry-run flag, idempotency key, CLI parity errors. |
| Notification hub | `GET /gui/notifications` (initial sync), `WS /ws/gui/notifications/{tenant}` | Stream governance/readiness/incident events; support ack/snooze/assign; resume via cursor. |
| Lineage & search | `GET /gui/artifacts/{id}/lineage`, `GET /gui/search`, `GET /gui/commands/history` | Provide lineage tree, search results, command history with audit metadata. |
| Prompt pack telemetry | `GET /gui/prompt-pack/templates/{id}/metrics`, `POST /gui/prompt-pack/templates/{id}/warmup` | Fetch telemetry snapshots, trigger warm-ups with streaming updates. |
| Readiness bridge | `POST /gui/readiness/waivers`, `POST /gui/readiness/attest`, `POST /gui/readiness/snooze` | Submit waivers/attestations, propagate governance events, enforce RBAC. |
| Automation hooks | `POST /gui/automation/webhooks/{template}` | Trigger signed webhooks for downstream automation (release, notifications). |

## Command Execution Flow

1. GUI sends `POST /gui/commands/{verb}` with payload, `dry_run`, `idempotency_key`, and audit headers (`X-Actor-Id`, `X-Tenant-Id`, `X-Trace-Id`).
2. Endpoint resolves OperationExecutor configuration, ensures feature flag/tenant authorized.
3. OperationExecutor runs in async task queue (existing worker). Endpoint streams status via websocket topic `/ws/gui/jobs/{tenant}`.
4. Upon completion, endpoint returns manifest metadata, telemetry IDs, and command history entry.
5. Duplicate idempotency key returns cached response; duplicates logged for governance.

## Notification Feed Design

- Backed by Redis Streams (`XADD`, `XREAD`) to allow fan-out and replay.
- Event payload schema: `{ event_id, cursor, tenant, category, severity, title, body, metadata, ack_state, created_at, expires_at }`.
- Websocket handshake accepts `last_cursor`; server replays via stream before switching to live publish.
- Ack/snooze/assign commands sent as control messages (`ACK`, `SNOOZE`, `ASSIGN`) over websocket or REST fallback; persisted to governance event log.

## Lineage & Search

- Lineage endpoint aggregates data from governance registry and artifact manifests, verifying hashes via `GovernanceRegistry.verify_manifest`.
- Search endpoint federates module indexes (coverage, mapping, overlay, readiness) using DuckDB or Elastic-like store; results include highlight snippets and governance metadata.
- Command history endpoint returns recent GUI-triggered commands with parameters, actor, status, manifest references.

## Readiness Bridge

- Waiver submissions validated against readiness policy (RBAC scope `readiness:approve`); stored via readiness service; governance event emitted.
- Attestations ensure preconditions (no unresolved failures unless waiver) before updating readiness manifest.
- Snooze requests include duration, reason, actor; propagate to notification stream and operations console.

## Observability & Rate Control

- Each adapter logs structured entries: `ts`, `tenant`, `actor`, `endpoint`, `verb`, `status`, `latency_ms`, `idempotency_key`, `trace_id`.
- Metrics: command counts, success/failure, retry rate, ack latency, snooze distribution, notification backlog length.
- Rate limits: per-tenant quotas (default 60 commands/min), burst tokens; 429 responses include `Retry-After`.
- Feature flags read from governance service; unauthorized features return 404.

## Security Posture

- Auth: JWT from existing identity provider; optional mTLS requirement for privileged endpoints (publish, readiness).
- CSRF: For REST, require `X-CSRF-Token` tied to session; websockets check CSRF token during handshake.
- Input validation: Pydantic schemas for payloads; enumerated command verbs; restrict automation templates to configured list.
- Audit headers mandatory; missing headers -> 400 with error code `AUDIT_HEADERS_REQUIRED`.

## Documentation & Tooling

- Maintain OpenAPI spec via FastAPI docs; export to `docs/gui/backend_adapters_api.md` using `scripts/generate_openapi.py`.
- Provide CLI parity table mapping `gui` endpoints to `domain determine` CLI commands.
- Include troubleshooting matrix (common error codes, remediation).

## Testing Plan

- Contract tests for each endpoint verifying status codes, payload structures, error handling, RBAC, feature flags.
- Integration tests comparing CLI vs GUI outputs for commands (using golden manifest hashes).
- Websocket tests simulating ack/snooze/resume cycles; measure ordering and duplication.
- Load tests with Locust or k6 focusing on notification stream and command endpoints under concurrent use.
- Security tests: replay attack prevention (idempotency+CSRF), authorization bypass attempts, rate-limit triggers.

## Risks & Mitigations

- **OperationExecutor latency**: Use async tasks and streaming updates; provide progress events.
- **Replay storms**: Cursor-based replay with bounding (e.g., 1k events max) and optional filters.
- **Multi-tenant data leakage**: All queries filtered by tenant scope; tests for cross-tenant contamination.
- **Feature flag misconfig**: Provide admin API to inspect feature flag state per tenant; fallback to safe defaults.
