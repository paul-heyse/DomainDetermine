# add-gui-operations – Design

## Context

Building on the GUI architecture and foundation, this change delivers operational capabilities: reviewer workbench, governance workflows, observability dashboards, deployment controls, and security/compliance tooling. The solution stays Python-native (NiceGUI + FastAPI adapters) to reuse DomainDetermine’s models, OperationExecutor, and telemetry infrastructure.

## Goals

- Provide a unified reviewer workbench covering mapping, overlay, eval adjudication, readiness waivers, and prompt pack calibration.
- Integrate governance registry workflows (waivers, signatures, manifest promotion, readiness attestations) with automation hooks.
- Surface operational dashboards for job queues, LLM cost, readiness gates, SOC alerts, and incidents, with ack/escalation flows.
- Define deployment automation (CI/CD, feature flags, rollout controls), incident workspaces, DR plans, and compliance reporting.
- Enforce enhanced security (MFA, session policies, device posture), retention policies, training materials, and runbooks.

## Non-Goals

- Implement module-specific data pipelines (already provided by services).
- Build external ticketing connectors beyond stub hooks—final integrations handled later.
- Replace existing CLI automation; GUI must remain parity-focused.

## Reviewer Workbench Architecture

- **Views**: Tabbed interface (`mapping`, `overlay`, `eval`, `readiness`, `prompt pack`) implemented in `src/DomainDetermine/gui/workspaces/operations.py`, using NiceGUI data tables and detail panels.
- **Data sources**: FastAPI adapters under `/gui/reviewer/*` (mapping batches, overlay proposals, eval incidents, readiness gates, prompt diagnostics).
- **Actions**: Approve/override/defer with reason codes; bulk selection; offline queue for deferred submissions; CLI copy per action.
- **Evidence panels**: Show source text, LLM rationales, pilot metrics, telemetry snapshots. Leverage Markdown/JSON viewers.
- **Collaboration**: Presence indicators and threaded comments via `/ws/gui/collab/{artifact}` with conflict handling.
- **SLA tracking**: Visual timers, queue metrics, and escalation thresholds (e.g., mapping backlog > 24h triggers alert banner).

## Governance Workflow Integration

- **Waiver management**: `/gui/governance/waivers` list and detail view; approvals capture signatures (FIDO2, TOTPs) and justification.
- **Manifest promotion**: Workflow wizard verifying prerequisites (readiness gates, waivers, sign-offs) before calling OperationExecutor via adapters.
- **Delegated approvals**: Admin view to configure delegation (RBAC matrix). Config stored in governance registry; UI shows active delegations and expiry.
- **Automation hooks**: For each approval/promotion event, GUI exposes copy-as-CLI and optional webhook trigger (configurable per tenant).

## Observability & Operations Console

- **Dashboards**: Built with `plotly`/`altair` inside NiceGUI to show LLM usage, job queue depth/latency, readiness pass rates, cost trends, SOC events.
- **Alerting**: Configurable thresholds stored via `/gui/admin/alerts`. Alerts appear in notification center and operations console; ack updates event bus.
- **Incident timeline**: Chronological view of incidents, escalations, actions, and resolution notes; integrates with SOC feed via asynchronous adapter.
- **Admin console**: Summaries of release versions, feature flags, readiness status, active incidents, and automation status.

## Deployment & Release Controls

- **CI/CD integration**: GUI admin panel retrieves pipeline status (GitHub Actions, Jenkins, etc.) via webhooks; displays current rollout stage.
- **Blue-green/canary**: Feature flag toggles allow shifting user cohorts; metrics monitor health before promoting.
- **Rollback**: Single-click rollback triggers OperationExecutor command with idempotency key; UI logs reason and result.
- **Shadow deployments**: Staging tenants run read-only copy; metrics compared against production. GUI shows diff summary.
- **Chaos/DR drills**: Schedule drills, track completion, gather outcomes; store runbook links.

## Security & Compliance Enhancements

- **Session policies**: Extend foundation features with device fingerprinting, location checks, just-in-time access permissions.
- **MFA**: Integrate graphical MFA enrollment/prompts (TOTP/WebAuthn) via governance services; UI surfaces fallback paths, recovery codes, and enforcement status per tenant.
- **SOC integration**: Websocket feed from SIEM to incident workspace; ack/escalation actions propagate back via adapter.
- **Retention engine**: Cron job (celery beat / APScheduler) runs retention tasks; GUI surfaces upcoming deletions and audit trail.
- **Security event logging**: All login/logout/MFA/device posture events generate audit entries, visible in admin console and exported for compliance.
- **Training & onboarding**: Guided tours built with NiceGUI overlays; onboarding checklist stored per user; knowledge checks recorded.
- **Runbooks**: Markdown viewer linking to docs; access logged for compliance.

## Data & Event Flow

1. Reviewers load workbench; initial data fetched via REST, live updates via websockets.
2. Actions generate POST/PATCH requests with `X-Actor`, `X-Trace`, `X-Idempotency` headers; backend logs and persists.
3. Alerts from telemetry service broadcast via `/ws/gui/notifications` and mirrored in operations console.
4. Deployment status updates consumed via webhook subscription, stored in Redis; NiceGUI poller updates dashboards.

## Testing & Validation Strategy

- **Unit/UI tests**: Snapshot tests of workbench components, routing, command palette integration.
- **Integration tests**: Mock adapters verifying ack/escalation, waiver approvals, manifest promotion flows, retention tasks.
- **Resilience tests**: Simulate network failure, queue backlog, failed approvals; ensure UI messaging and retries work.
- **Security tests**: MFA flow, session timeout, delegated approvals misuse, retention enforcement; run with security stakeholders.
- **UAT**: Cross-functional pilot with reviewers, governance, ops; capture feedback in `docs/gui/operations_pilot.md`.

## Deliverables

- `gui/reviewer/` components & services.
- `gui/operations/` dashboard + admin console components.
- `gui/governance/` workflows for waivers and promotions.
- `tests/gui_operations/` integration suite.
- Documentation: runbooks, training materials, onboarding guide updates.

## Risks & Mitigations

- **Complexity**: Workbench spans multiple modules; mitigate by modular components per workflow and feature flags.
- **Performance**: Large queues or telemetry streams may affect UI; use pagination, delta updates, and virtualization.
- **Security**: Privileged actions require strong audit; use mandatory trace IDs, signature capture, and double-confirmation dialogs.
- **Change management**: Provide thorough training and CLI parity to avoid operator resistance.
