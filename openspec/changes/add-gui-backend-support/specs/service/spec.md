## ADDED Requirements

### Requirement: GUI-Oriented API Surface

The service SHALL expose GUI-optimized REST and GraphQL endpoints—implemented with FastAPI/Pydantic and other Python libraries—for dashboard metrics, artifact lineage, job orchestration, notifications, search, and user preferences, reusing existing domain logic while enforcing RBAC, pagination, caching, and audit logging.

#### Scenario: Fetch dashboard metrics

- **WHEN** the GUI issues `GET /gui/metrics?tenant=...`
- **THEN** the service SHALL return aggregated ingestion, coverage, mapping, overlay, prompt pack, readiness, and cost metrics with timestamps, tenancy filters, and audit headers.

#### Scenario: GraphQL lineage query

- **WHEN** the GUI queries the lineage GraphQL API for an artifact ID
- **THEN** the service SHALL return upstream/downstream artifacts, manifests, waivers, and approval status with pagination, respecting licensing policies.

### Requirement: Real-time Streaming & Notifications

The service SHALL provide websocket or Server-Sent Event endpoints—built with Python async frameworks—for real-time job status, notifications, calibration updates, readiness gates, and cost alerts with fallback mechanisms.

#### Scenario: Subscribe to job stream

- **WHEN** the GUI subscribes to `/gui/stream/jobs/{job_id}`
- **THEN** the service SHALL stream status changes, logs, and completion events, handling reconnection and emitting governance audit logs.

#### Scenario: Notification feed delivery

- **WHEN** a waiver requires approval
- **THEN** the notification pipeline SHALL push a notification payload to subscribed clients and persist it in the inbox store with RBAC filtering.

### Requirement: Search & Indexing

The service SHALL maintain search indices—using Python search/indexing libraries—for artifacts (coverage plans, mappings, overlays, prompt packs, readiness reports) and expose search endpoints supporting filters, relevance ranking, and faceting.

#### Scenario: Search coverage plans

- **WHEN** the GUI calls `GET /gui/search?type=coverage-plan&query=merger`
- **THEN** the service SHALL return paginated results with metadata (version, status, waivers) and highlight matches.

### Requirement: User Preferences & Saved Views

The service SHALL provide APIs—implemented with Python persistence layers—to manage user preferences, saved dashboard views, inbox filters, and layout settings with tenant isolation and policy enforcement.

#### Scenario: Save dashboard view

- **WHEN** a user calls `POST /gui/preferences/views` with layout data
- **THEN** the service SHALL validate the payload, persist it scoped to the user/tenant, and return an identifier for reuse.

### Requirement: Notification & Event Pipeline

The service SHALL deliver GUI inbox items and alerts via background pipelines (queue/event bus) implemented with Python tooling (Celery/Dramatiq/Redis/etc.), supporting retry, deduplication, SLA tracking, and audit linkage.

#### Scenario: Event fan-out retry

- **WHEN** a notification delivery fails
- **THEN** the pipeline SHALL retry with exponential backoff, mark the notification as pending, and alert the operations dashboard if retries exceed thresholds.

### Requirement: Security, Governance & Observability

All GUI-related APIs SHALL enforce RBAC, rate limits, CSRF protections, tenant scoping, governance event logging, and emit OpenTelemetry traces/metrics tailored for GUI monitoring using Python middleware and observability libraries.

#### Scenario: Unauthorized access attempt

- **WHEN** a user without proper role accesses `/gui/metrics`
- **THEN** the service SHALL return HTTP 403, log the attempt with audit metadata, and increment security metrics.

#### Scenario: Trace GUI request

- **WHEN** a GUI request is processed
- **THEN** the service SHALL emit traces/metrics with attributes (`gui_workspace`, `tenant`, `artifact_type`) for observability dashboards.
