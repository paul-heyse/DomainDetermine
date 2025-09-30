## ADDED Requirements

### Requirement: GUI Command & Diff Adapters
The service SHALL expose GUI-focused REST endpoints that wrap OperationExecutor flows, diff generators, readiness runners, and manifest loaders to execute commands (dry-run or apply) and return structured responses with audit metadata, CLI parity, and error code standardization.

#### Scenario: Execute plan diff via GUI endpoint
- **WHEN** the GUI calls `POST /gui/commands/plan/diff` with request payload
- **THEN** the service SHALL validate auth headers, invoke the underlying OperationExecutor diff command, stream progress, and return structured diff results with trace ID, governance metadata, and CLI-equivalent payload.

#### Scenario: Dry-run ingest command
- **WHEN** the GUI posts to `/gui/commands/ingest` with `dry_run=true`
- **THEN** the service SHALL execute the dry-run path, produce no side effects, return a preview payload matching CLI dry-run output, and log audit metadata.

#### Scenario: Automation webhook trigger
- **WHEN** the GUI triggers `/gui/commands/release/promote`
- **THEN** the service SHALL validate approvals, execute the release workflow, emit automation webhooks, and return structured status updates.

### Requirement: Notification & Acknowledgement Bridge
The service SHALL provide REST/websocket notification feeds with acknowledgement, snooze, assignment, and escalation workflows, persisting state with audit trails and SLA tracking.

#### Scenario: Acknowledge waiver notification
- **WHEN** a user acknowledges a waiver notification via `/gui/notifications/{id}/ack`
- **THEN** the service SHALL mark the notification as acknowledged, record actor/reason/time, broadcast the state change to other subscribers, and update SLA metrics.

#### Scenario: Snooze incident alert
- **WHEN** a user snoozes a cost overrun alert
- **THEN** the service SHALL adjust notification schedules, persist intent, and ensure follow-up notifications after the snooze window.

### Requirement: Lineage Snapshot & Prompt Telemetry APIs
The service SHALL expose GUI endpoints to retrieve artifact lineage snapshots, prompt pack readiness telemetry, calibration history, and diff reports with signed manifest verification and license enforcement.

#### Scenario: Retrieve lineage snapshot
- **WHEN** the GUI requests `/gui/artifacts/{id}/lineage`
- **THEN** the service SHALL return upstream/downstream artifacts, manifests, waivers, prompts, and diff metadata, verifying signatures and respecting license masks.

#### Scenario: Fetch prompt readiness metrics
- **WHEN** the GUI queries `/gui/prompt-metrics`
- **THEN** the service SHALL return readiness scores, calibration stats, warm-up status, cost usage, drift alerts, and recommended remediation actions.

### Requirement: Readiness Waiver & Governance Bridge
The service SHALL expose endpoints for submitting readiness waivers, approvals, deployment gate decisions, and attestation records with policy validation, CLI parity, and governance event linkage.

#### Scenario: Submit readiness waiver from GUI
- **WHEN** the GUI posts a waiver payload to `/gui/readiness/waivers`
- **THEN** the service SHALL validate policy, persist the waiver, trigger governance events, notify subscribers, and expose follow-up tasks.

#### Scenario: Approve deployment gate via GUI
- **WHEN** an approver calls `/gui/gates/{id}/approve`
- **THEN** the service SHALL verify permissions, record approval, and update release manifest and governance logs.

### Requirement: Search Index & Command History APIs
The service SHALL provide search endpoints and command history APIs for GUI usage, allowing operators to browse past command executions, filter by tenant/module, and export results for compliance.

#### Scenario: Search command history
- **WHEN** the GUI queries `/gui/commands/history?tenant=XYZ&status=failed`
- **THEN** the service SHALL return paginated command records with metadata, error details, and links to artifacts/logs.

### Requirement: Rate Limiting, Caching & Feature Flags
All GUI adapter endpoints SHALL enforce per-tenant rate limits, caching policies, and feature flag headers to enable gradual rollout and protect service resources. Endpoints SHALL provide informative throttling responses and fallback behaviors.

#### Scenario: Rate limit exceeded
- **WHEN** a tenant exceeds configured request limits for command endpoints
- **THEN** the service SHALL respond with HTTP 429, include rate limit headers, log the event with telemetry, and ensure no backend execution occurs.

#### Scenario: Feature flag disabled
- **WHEN** a tenant without access invokes a beta endpoint
- **THEN** the service SHALL return HTTP 404/403 per policy, log the access attempt, and instruct the GUI to hide the feature.

### Requirement: Observability & Audit Integration
GUI adapter endpoints SHALL emit structured logs, OpenTelemetry spans, and governance events for each operation, capturing actor, tenant, command name, parameters, duration, and outcome, enabling parity with CLI audit records and cost tracking.

#### Scenario: Audit command execution
- **WHEN** a GUI command completes
- **THEN** the service SHALL emit a governance event with command details, actor, parameters, result, and correlation IDs, aligned with audit policy.

#### Scenario: Emit telemetry for notification delivery
- **WHEN** a notification is delivered via websocket
- **THEN** the service SHALL log delivery status, latency, retries, and subscriber information for observability dashboards.
