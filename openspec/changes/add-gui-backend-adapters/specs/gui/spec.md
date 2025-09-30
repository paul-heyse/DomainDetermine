## ADDED Requirements

### Requirement: GUI Command Execution Endpoints

Service layer SHALL expose REST endpoints that wrap existing CLI OperationExecutor flows, enabling GUI-triggered ingest, plan, audit, eval, readiness, and publish operations with dry-run support, audit headers, and typed error responses.

#### Scenario: GUI initiates plan job via adapter

- **WHEN** the GUI issues `POST /gui/commands/plan` with plan configuration and dry-run flag
- **THEN** the service SHALL invoke the OperationExecutor path used by the CLI, stream job updates, and return manifest metadata with identical audit and telemetry behavior.

#### Scenario: CLI parity error translation

- **WHEN** an adapter endpoint encounters the same validation error a CLI invocation would raise (e.g., missing manifest field)
- **THEN** the service SHALL return a structured error payload (error code, message, remediation hints, trace id) mirroring CLI semantics and log the failure with governance context.

### Requirement: Websocket Notification Feed & Incident Stream

Service SHALL provide websocket topics delivering governance, readiness, job, prompt pack, cost, and incident events normalized for GUI clients, supporting acknowledgement, snooze, assignment, escalation, and replay semantics.

#### Scenario: Acknowledge governance alert

- **WHEN** the GUI sends `ACK` for an alert over the websocket feed
- **THEN** the service SHALL mark the event as acknowledged, persist actor/timestamp, and broadcast state change to subscribers within the tenant scope.

#### Scenario: Resume feed after reconnect

- **WHEN** a GUI client reconnects with a last event cursor
- **THEN** the service SHALL replay missed events in order, enforce tenant scoping, and resume live streaming without duplicating acknowledgements or assignments.

#### Scenario: Assignment/escalation update

- **WHEN** an alert is assigned or escalated via the GUI
- **THEN** the service SHALL broadcast the updated state (assignee, escalation tier, timestamp) to subscribed clients, persist audit metadata, and synchronize with ticketing/chatops systems where configured.

#### Scenario: Snooze readiness alert

- **WHEN** a GUI client sends a snooze request for a readiness alert over the websocket feed
- **THEN** the service SHALL record the snooze metadata (actor, duration, reason), suppress repeat notifications for the specified window, and broadcast the updated state to the tenant's subscribers and audit log.

#### Scenario: Notification unsubscribe

- **WHEN** a user unsubscribes from a notification category via websocket control messages
- **THEN** the service SHALL update tenant-scoped preference records, adjust fan-out filters, and confirm the change without affecting other tenants.

### Requirement: Artifact Lineage Snapshot API

Service SHALL expose endpoints returning consolidated lineage snapshots (artifact metadata, upstream/downstream references, signature hashes) optimized for GUI diff viewers.

#### Scenario: Fetch lineage tree for artifact

- **WHEN** the GUI calls `GET /gui/artifacts/{id}/lineage`
- **THEN** the service SHALL return normalized JSON with artifact details, upstream/downstream IDs, signatures, and governance status suitable for diff rendering.

#### Scenario: Manifest hash verification

- **WHEN** the GUI requests a manifest download via the lineage API
- **THEN** the service SHALL validate the stored hash/signature against the governance registry before streaming the file and include verification metadata in the response.

### Requirement: Prompt Pack Telemetry Adapter

Service SHALL offer endpoints to retrieve prompt template metrics, calibration outcomes, and readiness state for GUI consumption, including warm-up status and constraint adherence statistics.

#### Scenario: Retrieve prompt pack health

- **WHEN** the GUI requests `GET /gui/prompt-pack/templates/{id}/metrics`
- **THEN** the service SHALL return template version, constraint adherence, calibration metrics, and warm-up readiness flags.

#### Scenario: Prompt calibration diff fetch

- **WHEN** the GUI requests telemetry deltas for a prompt
- **THEN** the service SHALL provide calibration changes since a supplied snapshot (pass/fail counts, drift metrics) enabling GUI diff displays.

#### Scenario: Trigger prompt warm-up via adapter

- **WHEN** the GUI posts to `/gui/prompt-pack/templates/{id}/warmup`
- **THEN** the service SHALL enqueue the warm-up job, return job identifiers, stream status updates via the notification feed, and ensure readiness manifests are updated on completion.

### Requirement: Artifact Search & Saved Views

Service SHALL expose search and saved-view APIs for GUI consumption, covering artifacts (coverage plans, mappings, overlays, prompt packs, readiness manifests) with ranking, filtering, relevance metadata, and tenant-scoped saved filters.

#### Scenario: Artifact search query

- **WHEN** the GUI calls `GET /gui/search` with query parameters (text, module, tags, status)
- **THEN** the service SHALL return paginated, relevance-ranked results including artifact metadata, governance state, highlight snippets, and next-page cursors while enforcing RBAC/licensing constraints.

#### Scenario: Save reviewer view

- **WHEN** a reviewer posts `POST /gui/preferences/views` with filters and column configuration
- **THEN** the service SHALL persist the saved view scoped to the tenant/user (or team if shared), return a view identifier, and include audit metadata for governance tracking.

### Requirement: Readiness & Waiver Bridge

Service SHALL expose APIs for GUI to submit readiness waivers, attestations, and snooze actions, enforcing RBAC, audit logging, and governance event propagation.

#### Scenario: Submit readiness waiver via GUI

- **WHEN** an authorized reviewer submits a waiver through `POST /gui/readiness/waivers`
- **THEN** the service SHALL validate RBAC, persist the waiver, emit governance events, and return updated readiness status to the GUI feed.

#### Scenario: Readiness attestation submission

- **WHEN** a readiness lead acknowledges a gate via `POST /gui/readiness/attest`
- **THEN** the service SHALL validate prerequisites, update readiness manifests, propagate events to telemetry feeds, and return the attested manifest hash.

### Requirement: Observability & Rate Controls

Service SHALL instrument GUI adapter endpoints with OpenTelemetry spans, structured logs tagged with GUI actors, and apply tenant-aware rate limits to prevent noisy clients from impacting core services.

#### Scenario: Rate limit triggered

- **WHEN** a tenant exceeds configured GUI adapter request rate
- **THEN** the service SHALL respond with 429, include retry metadata, and emit telemetry indicating the throttle event.

#### Scenario: Security header enforcement

- **WHEN** a GUI adapter request is missing required audit headers (trace id, actor, tenant)
- **THEN** the service SHALL reject the request with a 400 error, log the violation, and surface the issue via observability dashboards.

### Requirement: Authentication, RBAC & Feature Flag Headers

GUI adapter endpoints SHALL enforce the same authentication mechanisms as existing services (JWT/mTLS + optional MFA), honor module-level RBAC checks, and require feature-flag headers to guard early access functionality without exposing unauthorized data.

#### Scenario: Unauthorized command blocked

- **WHEN** a user lacking coverage planner privileges calls `/gui/commands/plan`
- **THEN** the service SHALL return 403 with RBAC context, log the attempt, and omit sensitive details from the response body.

#### Scenario: Feature flag gating

- **WHEN** a tenant without the `gui.overlay` feature flag accesses overlay adapters
- **THEN** the service SHALL respond with 404 (not enabled), record the access attempt, and avoid loading overlay data pipelines.

### Requirement: CLI Parity & Idempotency Guarantees

GUI adapters SHALL maintain parity with CLI side effects and provide idempotency via request identifiers so repeated submissions (due to retries/offline recovery) do not duplicate jobs or manifests.

#### Scenario: Idempotent command retry

- **WHEN** the GUI retries a publish command with the same idempotency key after a network failure
- **THEN** the service SHALL detect the duplicate, return the original result (manifest references, telemetry ids), and avoid creating duplicate artifacts.
