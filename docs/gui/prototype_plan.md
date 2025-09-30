# GUI Architecture Prototype & Validation Plan

## Purpose

This plan outlines how we will execute Section 5 of the `add-gui-architecture` tasks: rapid interaction prototypes, contract/integration test scaffolding, stakeholder validation, and collaboration pilots. All activities use the Python-native stack defined in `openspec/changes/add-gui-architecture/design.md` (NiceGUI on FastAPI).

## Prototype Milestones

| Milestone | Description | Deliverables | Stakeholders |
| --- | --- | --- | --- |
| P1 – Workspace Shell | Scaffold NiceGUI shell (layout, navigation, auth) with fake data sources | `prototype/main.py`, module scaffolds under `gui/`, screenshots/recording | GUI infra, governance |
| P2 – Module Spots | For each workspace, produce targeted view with stubbed adapters | `prototype/<workspace>.py` modules, annotated flows | Module leads (ingestion, coverage, mapping, overlay, eval, readiness, prompt pack, governance, service) |
| P3 – Job/Notification Streaming | Demonstrate websocket-driven job status & notification center using fixture feeds | Recorded demo, latency metrics, load notes | Operations, service SRE |
| P4 – Offline / Idempotency | Simulate offline queue (sqlitedict) and replay after reconnect, capture logs | Test script, audit log sample | Governance, readiness |
| P5 – Collaboration & Deep Links | Implement collaboration channel + shareable deep link for mapping review | Prototype branch, deep-link payload examples | Reviewer workbench owners |

## Prototype Environment

- **Runtime:** `micromamba run -p ./.venv python prototype/main.py`
- **Frameworks:** NiceGUI, FastAPI, Redis (Docker) for cache, sqlitedict for offline queue, fastapi-websocket-pubsub for streaming stubs.
- **Repository layout:** Commit `prototype/__init__.py`, `prototype/main.py`, and one module per workspace (e.g. `prototype/ingestion.py`) alongside a NiceGUI router that mirrors the skeleton app.
- **Data:** Frozen fixtures from `tests/fixtures/gui/` representing KOS snapshots, coverage plans, mapping batches, prompt telemetry, readiness gates, governance manifests.
- **Auth:** Use FastAPI dependency stubs returning demo JWT claims; real integration deferred to implementation stage.

## Acceptance Criteria per Task

### Task 5.1 – Interaction Prototypes & Usability Reviews

- Prototype screens cover critical workflows for every workspace (ingestion through service ops).
- At least one recorded walkthrough (<10 min) per module with module lead feedback captured in `docs/gui/usability_notes.md`.
- Accessibility tooling: run `pa11y` against prototype routes; include reports in `prototype/reports/accessibility/`.

### Task 5.2 – Contract & Integration Validation

- Create FastAPI test harness (`tests/gui_adapters/`) with stubbed adapters verifying pagination, filtering, RBAC rejections, idempotency behavior.
- Implement websocket replay test verifying cursored resume and acknowledgement flows.
- Document results in `docs/gui/contract_validation.md` with links to pytest outputs.

### Task 5.3 – Security & Compliance Review

- Facilitate review session with security/compliance stakeholders; log attendees, findings, and mitigations in `docs/gui/security_review.md`.
- Validate tenancy, RBAC, data residency, and feature flag behaviors using mock tenants (EU-only vs Global) in prototype.
- Provide checklist mapping requirements to prototype evidence.

### Task 5.4 – Collaboration Pilot

- Host pilot session with cross-functional cohort (mapping reviewers, overlay editors, readiness leads, operations).
- Capture feedback and incident reports in `docs/gui/collaboration_pilot.md` with action items.
- Demonstrate deep-link persistence and annotation sync using recorded session.

### Task 5.5 – OpenSpec Validation

- Run `openspec validate add-gui-architecture --strict` after each milestone update.
- Maintain change log in `openspec/changes/add-gui-architecture/notes.md` summarizing progress toward approval.

## Timeline & Owners

| Week | Focus | Owner |
| --- | --- | --- |
| W1 | Shell, module prototypes (P1–P2) | GUI lead |
| W2 | Streaming, offline resilience (P3–P4) | Service engineer |
| W3 | Collaboration pilot, security review (P5, Task 5.3) | Governance lead |
| W4 | Consolidated feedback, spec updates, validation | Cross-functional |

## Risks & Mitigations

- **Performance constraints:** If NiceGUI struggles with large tables, benchmark Panel/AgGrid fallback while keeping Python-only requirement.
- **Fixture drift:** Automate fixture regeneration from current manifests using `scripts/gui/make_fixtures.py` to avoid stale data.
- **Stakeholder bandwidth:** Schedule usability and pilot sessions during weekly module syncs; provide async recordings for feedback.
- **Offline queue correctness:** Use contract tests with forced network failure to guarantee idempotency and audit logging.

## Next Actions

1. Scaffold `src/DomainDetermine/gui/` package with NiceGUI app skeleton (`gui/app.py`, `gui/views/dashboard.py`) and ensure `prototype/main.py` exercises those modules.
2. Create fixtures pipeline and commit baseline data sets.
3. Book usability and security review sessions; create shared agenda docs.
4. Draft contract test suite skeleton in `tests/gui_adapters/test_adapters.py`.
5. Update OpenSpec tasks as milestones complete.
