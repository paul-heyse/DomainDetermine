## ADDED Requirements

### Requirement: Module Workspaces

The GUI SHALL provide dedicated workspaces for each DomainDetermine capability (Module 1 KOS ingestion, Module 2 coverage planner, Module 3 mapping, Module 4 overlay, Module 5 auditor, Module 6 eval generator, readiness operations, prompt pack stewardship, governance registry, service operations) enabling full task execution without CLI access while preserving module guardrails, SLAs, and governance checkpoints.

#### Scenario: Launch ingestion workspace

- **WHEN** an operator navigates to the ingestion workspace
- **THEN** the GUI SHALL surface source catalogs, connector manifests, telemetry timelines, queue controls, validation summaries, and lineage links so ingest jobs can be configured, queued, monitored, audited, and documented end-to-end.

#### Scenario: Mapping console human review

- **WHEN** reviewers open the mapping workspace
- **THEN** the GUI SHALL display batch results, LLM rationales, candidate logs, prompt health metrics, review queues with approve/defer workflows, escalation actions, and shall persist decisions to the governance registry with full audit trace.

#### Scenario: Coverage planner allocation workflow

- **WHEN** a planner operates in the coverage workspace
- **THEN** the GUI SHALL provide multi-level concept navigation, fairness constraint editing, allocator outputs with diagnostics, what-if calculators, and publish/promotion actions backed by the coverage planner services.

#### Scenario: Overlay proposal vetting

- **WHEN** an overlay reviewer inspects a proposal
- **THEN** the GUI SHALL surface evidence bundles, pilot outcomes, drift alerts, waiver context, and approval/rollback controls while synchronizing decisions with overlay manifests.

#### Scenario: Eval suite orchestration

- **WHEN** an evaluation engineer schedules suite runs
- **THEN** the GUI SHALL support slice construction, grader assignment, warm-up verification, run scheduling with telemetry, and shall update eval manifests and readiness scorecards automatically.

#### Scenario: Readiness workspace gate review

- **WHEN** a readiness lead opens the readiness workspace
- **THEN** the GUI SHALL list recent gate runs, expose suite metrics and evidence, allow sign-off or deferral with justification, and synchronize results with readiness manifests, dashboards, and release pipelines.

#### Scenario: Governance registry operations

- **WHEN** a governance operator reviews manifests
- **THEN** the GUI SHALL present manifest diffs, dependency graphs, signature status, release promotion controls, and waiver prerequisites, integrating with audit trails and automation hooks.

#### Scenario: Service operations console

- **WHEN** a service operator inspects the service workspace
- **THEN** the GUI SHALL display job queue metrics, quota usage, slow query diagnostics, incident history, and provide remediation actions (pause jobs, trigger warmups) while emitting governance telemetry.

### Requirement: Workspace-Oriented APIs & Data Contracts

Backend services SHALL expose workspace-oriented APIs (REST/GraphQL/websocket/search) delivering module-specific data (concept trees, quotas, mapping batches, overlay proposals, audit findings, eval suites, readiness scorecards, prompt metrics, service health) with tenant scoping, caching, audit metadata, schema versioning, idempotent mutations, and alignment with existing Python data contracts.

#### Scenario: Coverage planner data fetch

- **WHEN** the GUI requests coverage planner strata data
- **THEN** the backend SHALL return structured payloads (concept trees, quota allocations, fairness metrics, waiver statuses, solver diagnostics) with pagination, filters, computed diffs, and delta subscriptions for live updates.

#### Scenario: Overlay proposal stream

- **WHEN** the overlay workspace subscribes to proposal events
- **THEN** the backend SHALL stream ordered state transitions (draft, pilot, approved, rejected), reviewer assignments, and waiver updates with replay support and tenant-scoped cursors.

#### Scenario: Prompt pack search

- **WHEN** a user searches prompt templates or calibration sets
- **THEN** the API SHALL return indexed results with schema metadata, readiness status, costs, and links to manifests, respecting RBAC and license flags.

### Requirement: Job Orchestration, Event Streams & Automation Hooks

The GUI SHALL orchestrate long-running jobs (ingest, plan, audit, eval, readiness pipelines, prompt warmups, release processes) via GUI controls, presenting statuses, logs, lineage pins, dependency graphs, SLA timers, automation webhooks, and retry/rollback actions with configurable alerting. Services SHALL publish job/event streams consumable by the GUI and CLI to preserve parity.

#### Scenario: Retry coverage plan build

- **WHEN** a coverage plan job fails
- **THEN** the GUI SHALL surface the failure, correlate related artifacts and upstream dependency changes, allow the operator to inspect logs and traces, adjust parameters, capture remediation notes, and requeue the job while emitting governance telemetry.

#### Scenario: Readiness pipeline orchestration

- **WHEN** an operator launches a readiness pipeline run from the GUI
- **THEN** the interface SHALL track suite execution in real time, surface failing suites with drill-down logs, capture remediation notes, and persist the resulting scorecard and manifest hash back to the governance registry.

#### Scenario: Trigger downstream automation

- **WHEN** a readiness gate passes in the GUI
- **THEN** the system SHALL allow triggering downstream automation (release pipeline, notifications) via signed webhooks or CLI command integration, recording approvals and providing rollback controls.

### Requirement: Artifact Diff, Versioning, Drift Detection & Search

Each workspace SHALL expose side-by-side diffs, version history, drift detection alerts, search/tagging, annotation workflows, and promotion pipelines for module artifacts (snapshots, plans, mappings, overlay nodes, prompt pack releases, certificates, suites, readiness scorecards) referencing governance manifests and dependency graphs while honoring CLI storage conventions.

#### Scenario: Compare coverage plan versions

- **WHEN** a user selects two plan versions
- **THEN** the GUI SHALL display quota deltas, fairness metric changes, solver parameter differences, associated waivers, impacted eval suites, and provide exportable diff reports linked to audit certificates and release manifests.

### Requirement: Prompt Pack & LLM Integration

Workspaces relying on LLMs SHALL integrate prompt pack metadata, schema versions, calibration sets, warm-up status, quota/latency/cost telemetry, guardrails configuration, and failure taxonomies while enabling manual warm-ups, overrides, or rollbacks with audit logging and alignment to prompt pack runtime APIs.

#### Scenario: View mapping prompt health

- **WHEN** a mapping operator opens the prompt panel
- **THEN** the GUI SHALL show prompt template versions, schema diffs, constraint adherence metrics, calibration outcomes, LLM readiness status, and provide warm-up/pause/rollback controls with confirmation dialogs.

#### Scenario: Prompt failure mitigation

- **WHEN** an eval judge prompt fails readiness checks
- **THEN** the GUI SHALL alert operators, present remediation options (rerun calibration, reduce load, rollback), and record actions taken with manifest updates and telemetry.

#### Scenario: Prompt readiness overview

- **WHEN** a prompt steward opens the readiness panel
- **THEN** the GUI SHALL aggregate readiness scores, calibration staleness, cost trends, recent incidents, and allow filtering by module while generating governance events for tracked regressions.

### Requirement: Governance, Readiness, Compliance & Release Hooks

Workspaces SHALL surface governance checkpoints (waivers, approvals, readiness gates, deployment gates, release manifests, compliance tasks) inline, enabling sign-off, waiver submission, manifest review, readiness attestation, release promotion/rollback, and policy impact analysis without CLI, while linking to existing governance models.

#### Scenario: Auditor waiver handling

- **WHEN** fairness checks trigger waivers
- **THEN** the auditor workspace SHALL allow operators to view waiver details, provide mitigation notes, attach evidence, submit justifications, approve/reject via RBAC workflows, capture signatures, and update governance logs with lineage references.

#### Scenario: Readiness gate attestation

- **WHEN** a readiness lead reviews a gate within the GUI
- **THEN** the interface SHALL surface gate metrics, evidence, policy thresholds, allow attestation or deferral with justification, notify stakeholders, and persist the decision to readiness manifests and governance telemetry.

#### Scenario: Release manifest promotion

- **WHEN** a release manager promotes a manifest
- **THEN** the GUI SHALL enforce required approvals, validate readiness gates, update the governance registry, publish notifications, and expose automation hooks for deployment and rollback.

### Requirement: Notification & Event Aggregation

The GUI SHALL ingest governance, readiness, service, prompt pack, and cost events into a normalized notification pipeline supporting acknowledgement, snoozing, escalation, and routing rules while retaining audit trails and parity with CLI alerts.

#### Scenario: Notification acknowledgement workflow

- **WHEN** an operator acknowledges a governance alert from the notification center
- **THEN** the GUI SHALL update acknowledgement status, record actor and timestamp in the governance event log, and optionally notify subscribed stakeholders of the acknowledgement.

#### Scenario: Snooze readiness alert

- **WHEN** a readiness alert is snoozed for a tenant
- **THEN** the GUI SHALL record the snooze metadata (actor, duration, reason), suppress repeat notifications for the window, and surface the snooze state in dashboards and audit logs.

### Requirement: Offline Resilience, Feature Flags & Extensibility

The GUI architecture SHALL support offline-aware caching, reconnect logic with exponential backoff, client-side action queues for transient failures, feature flag controls, and plugin/extensibility points to rollout workspace capabilities safely across tenants while allowing module-specific extensions.

#### Scenario: Network disruption during mapping review

- **WHEN** the GUI loses network connectivity mid-review
- **THEN** it SHALL preserve unsaved actions locally, show recovery status, retry submission once connectivity returns, and log the incident without duplicating actions.

#### Scenario: Feature flag rollout

- **WHEN** a new workspace feature is gated behind a feature flag
- **THEN** the GUI SHALL respect tenant-specific flag configuration, hide controls until enabled, support progressive rollout, and record activation events in the governance log.

#### Scenario: Tenant extension injection

- **WHEN** a tenant-specific extension is enabled
- **THEN** the GUI SHALL load the extension module within a sandbox, enforce resource limits, propagate telemetry, and allow administrators to disable or roll back the extension.

### Requirement: Extensibility, Plugin Model & CLI Integration

The GUI SHALL provide modular extension points for future modules, tenant-specific panels, or CLI automation hooks to register components, data providers, and scripted actions while enforcing sandboxing, versioning, approval workflows, and audit logging. The GUI SHALL offer “copy as CLI command” options and stay in lockstep with CLI automation.

#### Scenario: Generate CLI command from GUI action

- **WHEN** a user inspects job parameters in the GUI
- **THEN** the GUI SHALL offer an option to copy the equivalent CLI command (including flags) and context, preserving automation parity.

#### Scenario: Extension approval workflow

- **WHEN** a new GUI extension is submitted
- **THEN** the platform SHALL route the extension through security review, tenant enablement steps, audit logging, and status dashboards before activation.

### Requirement: Tenancy, RBAC & Data Residency Enforcement

The GUI platform SHALL enforce tenant isolation, module-level RBAC, region-specific data residency policies, and feature flag gating before fetching or rendering data, preventing cross-tenant leakage and complying with contractual boundaries.

#### Scenario: Unauthorized workspace access blocked

- **WHEN** a user lacking overlay reviewer privileges attempts to load overlay data for another tenant
- **THEN** the GUI SHALL deny access, emit a security audit event (actor, tenant, module, attempted action), and present guidance for requesting access without exposing sensitive metadata.

#### Scenario: Data residency enforcement

- **WHEN** a user in a restricted region accesses artifacts
- **THEN** the GUI SHALL serve data from compliant endpoints, mask restricted fields, and log residency attestations for audit purposes.

### Requirement: Deep Linking, State Restoration & Collaboration

Workspaces SHALL provide shareable deep links capturing filters, selections, timeline positions, diff context, and annotation threads, restoring state on load while validating RBAC/tenancy and recording link usage for collaboration analytics.

#### Scenario: Resume mapping review via deep link

- **WHEN** a reviewer opens a shared deep link to a specific mapping batch with filters
- **THEN** the GUI SHALL validate permissions, restore the batch selection and filter set, highlight pending tasks, and record the resume event for audit.

#### Scenario: Collaborative annotation thread

- **WHEN** multiple reviewers comment on an artifact via a deep link
- **THEN** the GUI SHALL synchronize the annotation thread, show presence indicators, and reconcile edits via conflict-handling rules while persisting comments to the governance record.
