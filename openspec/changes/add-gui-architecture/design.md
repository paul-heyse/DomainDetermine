# add-gui-architecture – Design

## Context

DomainDetermine’s operators currently interact with ingestion, coverage planning, mapping, overlay, auditing, readiness, prompt pack, governance, and service operations through CLI tooling and ad-hoc dashboards. The `add-gui-architecture` change establishes a Python-native GUI layer that brings these workflows into a cohesive, RBAC-aware interface while preserving determinism, manifest governance, and CLI parity. The design must align tightly with existing Python services (FastAPI, Typer CLI, governance registry) and reuse shared data contracts, telemetry, and security posture.

## Goals

- Provide a modular GUI architecture with dedicated workspaces for every module (1–6), readiness, prompt pack stewardship, governance registry, and service operations.
- Maintain a pure Python stack—NiceGUI (primary UI framework) mounted on FastAPI backends—to guarantee reuse of domain models, OperationExecutor flows, and telemetry.
- Deliver interaction models, API contracts, state management policies, and offline/feature-flag governance that satisfy OpenSpec requirements and support future implementation tasks.

## Non-Goals

- Building production-ready widgets or styling (covered by later implementation changes).
- Defining non-Python front-ends (React/TypeScript); the architecture standardizes on Python components.
- Shipping final deployment scripts; this document focuses on architectural blueprint and contracts.

## Technology Selections

| Concern | Decision | Rationale |
| --- | --- | --- |
| GUI framework | **NiceGUI** under `src/DomainDetermine/gui` mounted on FastAPI | Python-native, async-friendly, integrates with FastAPI routers already in DomainDetermine, provides component library, routing, and websocket support. |
| Layout styling | Tailwind for NiceGUI via `nicegui.tailwind` plug-in | Maintains consistent branding with minimal custom CSS; works fully in Python. |
| State/query management | `nicestore` (NiceGUI store) + `fastapi-websocket-pubsub` | Enables reactive updates without relying on JS frameworks; ties into existing async event loops. |
| Data caching | `asyncio` tasks with Redis-backed cache (via `aioredis`) | Supports tenant-aware query caching and offline recovery. |
| Background jobs | Existing OperationExecutor workers, triggered via FastAPI endpoints | Maintains CLI parity and idempotency semantics. |
| Streaming | FastAPI websocket endpoints with `fastapi-websocket-pubsub`; NiceGUI `ui.run_javascript` wrappers | Provides real-time updates for jobs, notifications, readiness alerts. |
| Offline queue | Local `sqlite` queue (via `sqlitedict`) persisted through NiceGUI store | Preserves actions while offline, replays with idempotency keys. |
| Feature flags | `flipper-client` (Python) consuming governance feature flag service | Aligns with governance-managed rollout policies. |
| Authentication | Existing FastAPI auth middleware (JWT + optional mTLS) reused in NiceGUI router | Ensures single auth stack for CLI/API/GUI. |

## Bootstrap Deliverables

- Create `src/DomainDetermine/gui/__init__.py` and `src/DomainDetermine/gui/app.py` that mount the NiceGUI application on the existing FastAPI instance, register shared dependencies (auth, telemetry, feature flags), and expose a `create_app()` factory used by CLI and tests.
- Add `src/DomainDetermine/gui/workspaces/__init__.py` with placeholder registration hooks for each workspace so future changes can append views without restructuring the package.
- Provide `scripts/gui/dev_server.py` (or Typer command) that launches the skeleton app, serving placeholder pages for each workspace with health/status indicators to unblock smoke tests.
- Introduce `tests/gui/test_skeleton.py` validating the app factory loads, the root route renders, and health endpoints return 200 using the NiceGUI test client.

## Workspace Interaction Models

Each workspace includes a top-level dashboard, detail panels, action drawers, and CLI parity controls (“copy as CLI”, dry-run toggles). Offline-friendly banners and telemetry overlays are standard across workspaces.

### Module 1 – KOS Ingestion Studio

- **Navigation:** Source catalog listing, connector manifests, run history timeline, validation summary panel.
- **Key interactions:**
  - Configure connector (select source, credential profile, fetch cadence, license policy) and submit ingestion jobs via `/gui/commands/ingest` adapter.
  - Monitor job progress with live logs streamed over websocket; drill into SHACL/tabular validation output.
  - Compare snapshots (hashes, release versions) and promote to governance registry.
- **Offline/resume:** Job submissions queued with idempotency key; UI replays last known state after reconnect.

### Module 2 – Coverage Planner Console

- **Navigation:** Concept tree explorer (prefetched via coverage APIs), fairness constraint editor, allocation dashboards, what-if calculators.
- **Key interactions:**
  - Adjust constraints (floor/ceiling sliders, cost weights) and trigger solver run (`POST /gui/commands/plan`).
  - Inspect solver diagnostics, fairness metrics, waiver candidates.
  - Export plan diffs and attach mitigation notes before publishing to registry.
- **What-if:** Live calculators use cached solver outputs (DuckDB queries) with parameter binding; results update via websocket delta feed.

### Module 3 – Mapping Console

- **Navigation:** Batch list, search bar, candidate log viewer, review queue.
- **Key interactions:**
  - Review mapping decisions with source text, candidate metadata, LLM rationales.
  - Approve/override/defer with reason codes, immediately persisting via governance event bridge.
  - Warm-up prompt pack templates from the panel (calls prompt telemetry adapter).
- **Offline:** Decisions cached locally until ack confirmation; duplicates prevented via idempotency keys.

### Module 4 – Overlay Lab

- **Navigation:** Proposal kanban (draft / pilot / approved), evidence viewer, pilot metrics summary.
- **Key interactions:**
  - Review proposals with citations, run pilot annotation checks, attach waivers.
  - Approve/publish overlay nodes, triggering manifest updates.
  - Generate CLI command snippet for reproduction.
- **Policies:** Automatic duplicate detection ensures consistent decisions; license restrictions enforced when showing base KOS labels.

### Module 5 – Coverage Auditor Workspace

- **Navigation:** Certificate dashboard, fairness heatmaps, waiver queue.
- **Key interactions:**
  - Inspect structural checks, fairness metrics, drift analysis with diff visualizations.
  - Submit/approve waivers inline; attach evidence (documents hashed, stored in registry).
  - Promote certificate manifest with signature capture (USB key or Yubikey integration through FastAPI).

### Module 6 – Eval Suite Orchestrator

- **Navigation:** Suite list, slice configurator, grader assignment grid, run telemetry.
- **Key interactions:**
  - Build suite configuration, assign graders (deterministic or LLM), set thresholds.
  - Schedule runs (calls `/gui/commands/evalgen` and `/gui/commands/run`).
  - Monitor run health via live telemetry (slice results, failure details) with annotation features.

### Readiness Operations Workspace

- **Navigation:** Gate dashboard, recent runs, attestation log.
- **Key interactions:**
  - View gate metrics, supporting evidence, failure taxonomy.
  - Attest or defer gates; issue waivers with justification.
  - Trigger downstream automation (release pipeline) with signed webhooks.

### Prompt Pack Stewardship

- **Navigation:** Template catalog, schema diffs, calibration history, cost telemetry.
- **Key interactions:**
  - Inspect template versions, diff schema/parameters, view calibration stats.
  - Run warm-up or rollback (calls `/gui/prompt-pack/templates/{id}/warmup`).
  - Monitor constraint adherence and latency distributions; raise incident from anomalies.

### Governance Registry Workspace

- **Navigation:** Manifest tree, diff viewer, dependency graph, waiver tracker.
- **Key interactions:**
  - Compare manifest versions, inspect signature state, review dependency impacts.
  - Promote/demote manifests, capture signatures, manage waivers.
  - Visualize lineage graphs (IDs hashed to ensure deterministic layout).

### Service Operations Console

- **Navigation:** Job queue metrics, SLA charts, incident timeline, resource usage.
- **Key interactions:**
  - Pause/resume job queues, reprioritize tasks, trigger warm-up jobs.
  - Inspect incident log and escalate to SOC tools.
  - Monitor LLM cost, latency trends, readiness gating across tenants.

## Backend & Data Contracts

### API Design Principles

- All adapters implemented as FastAPI routers under `/gui/*`, using Pydantic models that mirror existing domain schemas (e.g., `CoveragePlan`, `MappingRecord`).
- Streaming endpoints use websocket topics with replay cursors (`cursor` query parameter) to support offline recovery.
- Search endpoints provide pagination (`cursor`, `limit`), sorting, filter support, and embed governance metadata (waiver counts, signature status).
- Every mutation requires audit headers: `X-Actor-Id`, `X-Tenant-Id`, `X-Trace-Id`, `X-Idempotency-Key` (for offline replay).

### Key Endpoint Families

| Workspace | Endpoint | Purpose |
| --- | --- | --- |
| Ingestion | `POST /gui/commands/ingest` | Submit ingestion job with configuration payload. |
| Coverage | `POST /gui/commands/plan` | Run coverage planner; returns job id and manifest preview. |
| Coverage | `GET /gui/coverage/strata` | Fetch strata tree, quotas, fairness diagnostics. |
| Mapping | `GET /gui/mapping/batches` | List mapping batches with status, metrics, filters. |
| Overlay | `GET /gui/overlay/proposals` | Fetch proposals by state; includes evidence hashes and pilot metrics. |
| Auditor | `GET /gui/auditor/certificates` | Return certificate metrics, drift analysis, pending waivers. |
| Eval | `POST /gui/commands/evalgen` | Generate eval suite with specified config. |
| Eval | `POST /gui/commands/run` | Launch eval run; streaming telemetry via websocket. |
| Readiness | `POST /gui/readiness/attest` | Submit gate attestation with signature details. |
| Prompt pack | `GET /gui/prompt-pack/templates/{id}/metrics` | Provide telemetry snapshot for template. |
| Governance | `GET /gui/governance/manifests` | List manifests, diffs, waiver counts. |
| Operations | `GET /gui/service/queues` | Provide queue depth, SLA metrics, incident markers. |

### Websocket Topics

- `/ws/gui/jobs/{tenant}`: job status updates (ingest, plan, eval, readiness).
- `/ws/gui/notifications/{tenant}`: governance, readiness, incident alerts with ack/snooze commands.
- `/ws/gui/prompt-pack/{tenant}`: prompt telemetry updates, calibration outcomes.
- `/ws/gui/collab/{artifact_id}`: deep link collaboration channel, presence indicators, comment updates.

All websocket messages include `event_id`, `cursor`, `timestamp`, `actor`, `payload`, and `signature` (governance signed event log reference) for auditability.

## State & Offline Policies

- **Query cache:** Tenant-scoped async caches (Redis) keyed by `tenant + endpoint + params + version`. TTLs derived from artifact update frequency (e.g., coverage strata TTL 5 min, job statuses TTL 5 s).
- **Optimistic updates:** Mutations immediately update local store; server confirmation reconciles state. Failed confirmation triggers error banner and suggests CLI fallback.
- **Offline queue:** Actions persisted via `sqlitedict` with `idempotency_key`. When connectivity restored, queue replay ensures monotonic commit order.
- **Drift detection:** Front-end polls for spec version mismatch (governance manifest `schema_version`). On mismatch, workspace prompts refresh and displays changelog summary pulled from `openspec` metadata.

## Security & RBAC Enforcement

- FastAPI dependencies enforce JWT validation, tenant binding, and role-based access (module-specific scopes like `workspace:coverage`, `workspace:readiness`).
- Feature flag middleware inspects `X-Feature-Flags` header set by governance service; unauthorized features return 404 to avoid leakage.
- CSRF tokens issued per session, validated on state-changing requests; NiceGUI integrates via `ui.form` hidden fields.
- Session policies: idle timeout 15 minutes (configurable per tenant), refresh token rotation, optional device posture validation (mTLS client cert or OS attestation).

## Telemetry & Observability

- Every GUI action logs: `ts`, `tenant`, `workspace`, `action`, `actor`, `artifact_id`, `status`, `latency_ms`, `trace_id`.
- NiceGUI integrates with OpenTelemetry via middleware capturing request spans, websocket spans, and client action traces.
- Metrics exported: workspace usage, job start/finish counts, candidate review throughput, waiver approval latency, prompt warm-up cost.
- Dashboards (Grafana) aggregate GUI metrics, correlate with backend operations, and trigger alerts (cost overruns, queue backlog, readiness regression).

## Collaboration & Deep Linking

- Deep link structure: `/gui/{workspace}?state=<base64-json>` where payload includes filters, selections, cursor, timeline position. Links signed with HMAC to prevent tampering.
- Collaboration presence: `collab` websocket channel broadcasts user presence (`user_id`, `workspace`, `artifact`, `last_action`). Concurrency conflicts resolved via last-writer-wins with audit log entries.
- Annotation threads stored via governance event store; NiceGUI markdown editor used for comments with versioned history.

## Testing & Validation Plan (Design-Stage)

- **Component prototypes:** Use NiceGUI preview mode to prototype each workspace view with stub data before full implementation.
- **Contract tests:** Write FastAPI test cases for `/gui/*` adapters validating RBAC, feature flags, schema compliance, and idempotency.
- **Offline simulations:** Use integration tests to cut network mid-actions, verifying queue replay and duplicate prevention.
- **Accessibility scans:** Integrate `pa11y` CLI (wrapped via Python subprocess) against rendered pages to enforce WCAG 2.1 AA compliance.
- **Performance budgets:** Define baseline latency targets (initial page load < 2.5 s, job orchestration commands < 300 ms server handling) for later measurement.
- **Prototype scaffolding:** Commit `prototype/` NiceGUI modules and `tests/fixtures/gui/` datasets referenced in the plan so usability reviews and contract tests consume repository-tracked assets instead of ad hoc files.

## Open Questions / Follow-Ups

- Final decision on embedded analytics engine (DuckDB server vs. pulling aggregates from services) will be resolved during implementation; current plan favors backend-precomputed aggregates.
- Evaluate NiceGUI vs. Panel for extremely large data tables (e.g., mapping candidates > 10k rows); may adopt hybrid approach if needed.
- Determine whether to leverage `asyncio.TaskGroup` for fan-out queries per workspace or central GraphQL gateway—prototype in subsequent tasks.
