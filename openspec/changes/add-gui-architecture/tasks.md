## 1. Specification & Approval

- [ ] 1.1 Map module-specific GUI requirements by reviewing Modules 1–6 specs and identifying GUI workflows.
- [ ] 1.2 Present architectural plan (workspace layout, data flow diagrams, RBAC) to module leads for approval.
- [x] 1.3 Capture readiness, prompt pack, governance registry, and service operations requirements from existing specs and incorporate into architecture brief. (See `design.md` summaries per workspace.)

## 2. GUI Workspace Design

- [x] 2.1 Define interaction models for Module 1 ingestion studio (source catalog, manifests, telemetry timelines).
- [x] 2.2 Define interaction models for Module 2 coverage planner (multi-level navigation, fairness editing, allocator diagnostics, what-if tools).
- [x] 2.3 Define interaction models for Module 3 mapping console (pipeline runs, review queue, crosswalk manager, prompt health overlays).
- [x] 2.4 Define interaction models for Module 4 overlay lab (proposal vetting, pilot tracking, waiver context, publication workflows).
- [x] 2.5 Define interaction models for Module 5 auditor (certificate reports, fairness analytics, waiver handling, release gating).
- [x] 2.6 Define interaction models for Module 6 eval generator (suite builder, grader config, warm-up orchestration, run telemetry).
- [x] 2.7 Define interaction models for readiness operations workspace (gate dashboards, attestation flows, automation triggers).
- [x] 2.8 Define interaction models for prompt pack stewardship (template search, calibration diffs, readiness health, warm-up controls).
- [x] 2.9 Define interaction models for governance registry workspace (manifest promotion, diff review, lineage visualization, release pipelines).
- [x] 2.10 Define interaction models for service operations console (job queue health, quota dashboards, incident views).
- [ ] 2.11 Scaffold the NiceGUI shell under `src/DomainDetermine/gui/` (app factory, workspace registry, health route) and add a Typer/CLI command for local dev server launch.

## 3. Backend & Data Contracts

- [x] 3.1 Specify APIs/GraphQL/search schemas for each workspace including pagination, filtering, streaming, replay cursors, and structured search facets.
- [x] 3.2 Document optimistic update, offline caching, action queue, and invalidation policies for artifacts, job state, prompt pack calibration, readiness telemetry, and notifications.
- [x] 3.3 Align telemetry, alert, audit, and incident event schemas (OpenTelemetry, governance, readiness, SOC) with GUI consumption requirements and collaboration features.
- [x] 3.4 Define feature flag taxonomy, rollout process, and plugin/extension model (registration, sandboxing, approvals) for workspace modules.
- [x] 3.5 Establish CLI parity guidelines (OperationExecutor reuse, idempotency keys, artifact storage locations, dry-run semantics) and error handling contracts.
- [x] 3.6 Define deep-link payload structure (filters, selections, thread context) and validation rules to support state restoration.

## 4. Cross-cutting Concerns

- [x] 4.1 Choose a Python-native component library/style system (Dash, Panel, NiceGUI, or equivalent) meeting accessibility and branding requirements, including RTL support, and document the selection rationale. (NiceGUI + Tailwind plugin documented in `design.md`.)
- [x] 4.2 Establish shared state management (query cache, websocket bus, collaboration presence) and error handling patterns.
- [x] 4.3 Define localization strategy, timezone handling, licensing notices, and tokenisation for prompt pack integration.
- [x] 4.4 Plan deployment target architecture (reverse proxy, CDN, auth gateway) with resilience, SLA timers, and automation hooks.
- [x] 4.5 Design tenancy/RBAC enforcement, data residency controls, and audit propagation strategy across workspaces.
- [x] 4.6 Define deep-linking, annotation, and collaboration UX patterns (shareable URLs, presence indicators, conflict resolution).

## 5. Testing & Validation

- [ ] 5.0 Commit NiceGUI prototype modules under `prototype/` and baseline fixtures under `tests/fixtures/gui/` matching the prototype plan paths.
- [ ] 5.1 Produce interaction prototypes (see `docs/gui/prototype_plan.md`) and run usability reviews with operators from each module (ingestion, coverage, mapping, overlay, eval, readiness, governance, service).
- [ ] 5.2 Validate data/search contracts against service stubs using the plan in `docs/gui/prototype_plan.md`; add contract/integration tests for streaming, replay, and CLI parity scenarios.
- [ ] 5.3 Review tenancy, RBAC, data residency, and feature flag planning with security/compliance stakeholders, logging outcomes per prototype plan.
- [ ] 5.4 Pilot collaboration features (deep links, annotations, assignment) with a cross-functional cohort and capture feedback following the prototype plan.
- [ ] 5.5 Execute `openspec validate add-gui-architecture --strict` at each milestone completion.
