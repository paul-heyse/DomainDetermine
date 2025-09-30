## 1. Specification & Approval

- [ ] 1.1 Map module-specific GUI requirements by reviewing Modules 1–6 specs and identifying GUI workflows.
- [ ] 1.2 Present architectural plan (workspace layout, data flow diagrams, RBAC) to module leads for approval.
- [ ] 1.3 Capture readiness, prompt pack, governance registry, and service operations requirements from existing specs and incorporate into architecture brief.

## 2. GUI Workspace Design

- [ ] 2.1 Define interaction models for Module 1 ingestion studio (source catalog, manifests, telemetry timelines).
- [ ] 2.2 Define interaction models for Module 2 coverage planner (multi-level navigation, fairness editing, allocator diagnostics, what-if tools).
- [ ] 2.3 Define interaction models for Module 3 mapping console (pipeline runs, review queue, crosswalk manager, prompt health overlays).
- [ ] 2.4 Define interaction models for Module 4 overlay lab (proposal vetting, pilot tracking, waiver context, publication workflows).
- [ ] 2.5 Define interaction models for Module 5 auditor (certificate reports, fairness analytics, waiver handling, release gating).
- [ ] 2.6 Define interaction models for Module 6 eval generator (suite builder, grader config, warm-up orchestration, run telemetry).
- [ ] 2.7 Define interaction models for readiness operations workspace (gate dashboards, attestation flows, automation triggers).
- [ ] 2.8 Define interaction models for prompt pack stewardship (template search, calibration diffs, readiness health, warm-up controls).
- [ ] 2.9 Define interaction models for governance registry workspace (manifest promotion, diff review, lineage visualization, release pipelines).
- [ ] 2.10 Define interaction models for service operations console (job queue health, quota dashboards, incident views).

## 3. Backend & Data Contracts

- [ ] 3.1 Specify APIs/GraphQL/search schemas for each workspace including pagination, filtering, streaming, replay cursors, and structured search facets.
- [ ] 3.2 Document optimistic update, offline caching, action queue, and invalidation policies for artifacts, job state, prompt pack calibration, readiness telemetry, and notifications.
- [ ] 3.3 Align telemetry, alert, audit, and incident event schemas (OpenTelemetry, governance, readiness, SOC) with GUI consumption requirements and collaboration features.
- [ ] 3.4 Define feature flag taxonomy, rollout process, and plugin/extension model (registration, sandboxing, approvals) for workspace modules.
- [ ] 3.5 Establish CLI parity guidelines (OperationExecutor reuse, idempotency keys, artifact storage locations, dry-run semantics) and error handling contracts.
- [ ] 3.6 Define deep-link payload structure (filters, selections, thread context) and validation rules to support state restoration.

## 4. Cross-cutting Concerns

- [ ] 4.1 Choose component library/style system meeting accessibility and branding requirements, including RTL support.
- [ ] 4.2 Establish shared state management (query cache, websocket bus, collaboration presence) and error handling patterns.
- [ ] 4.3 Define localization strategy, timezone handling, licensing notices, and tokenisation for prompt pack integration.
- [ ] 4.4 Plan deployment target architecture (reverse proxy, CDN, auth gateway) with resilience, SLA timers, and automation hooks.
- [ ] 4.5 Design tenancy/RBAC enforcement, data residency controls, and audit propagation strategy across workspaces.
- [ ] 4.6 Define deep-linking, annotation, and collaboration UX patterns (shareable URLs, presence indicators, conflict resolution).

## 5. Testing & Validation

- [ ] 5.1 Produce interaction prototypes and run usability reviews with operators from each module (ingestion, coverage, mapping, overlay, eval, readiness, governance, service).
- [ ] 5.2 Validate data/search contracts against service stubs; add contract/integration tests for streaming, replay, and CLI parity scenarios.
- [ ] 5.3 Review tenancy, RBAC, data residency, and feature flag planning with security/compliance stakeholders.
- [ ] 5.4 Pilot collaboration features (deep links, annotations, assignment) with a cross-functional cohort and capture feedback.
- [ ] 5.5 Execute `openspec validate add-gui-architecture --strict`.
