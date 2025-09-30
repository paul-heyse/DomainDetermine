## 1. Specification & Approval

- [ ] 1.1 Review service, governance, readiness, and prompt-pack specs; capture GUI scope, navigation map, accessibility/security requirements; draft `specs/gui/spec.md` updates.
- [ ] 1.2 Circulate proposal + navigation wireframes with ops, governance, security, and module owners; record approvals/notes.
- [ ] 1.3 Produce initial design brief (information architecture, auth flows, tenancy model) for reference during implementation.

## 2. Architecture & Infrastructure

- [ ] 2.1 Select frontend stack (component library, routing, state/query management, auth integration) and document rationale in `design.md`.
- [ ] 2.2 Define API contracts (REST/GraphQL/websocket) required for dashboards, artifact browsing, job/control, readiness telemetry, prompt pack metrics, notifications, preferences, and command palette actions; publish schema docs in `docs/gui/api.md`.
- [ ] 2.3 Provision build pipeline and hosting topology (static asset build, reverse proxy, CDN, auth gateway) with IaC stubs, blue/green deployment strategy, and deployment diagram.
- [ ] 2.4 Establish telemetry/logging standards for GUI (structured logs, OpenTelemetry spans, user actions, performance metrics) and align with existing observability stack.
- [ ] 2.5 Define session security, MFA, CSRF mitigation, feature-flag policy, offline handling strategy, and audit header propagation requirements with governance/security sign-off.

## 3. Implementation

- [ ] 3.1 Scaffold GUI project (monorepo or package), shared layout, theming, RBAC-aware navigation, command palette, notification center, audit log viewer, global search.
- [ ] 3.2 Implement dashboard widgets for pipeline health, artifact lineage, readiness status, cost alerts, governance alerts, and link-outs to module workspaces.
- [ ] 3.3 Wire GUI authentication (JWT/mTLS/SSO integration), MFA hooks, session management (timeouts, refresh), device posture checks, and telemetry logging compliant with governance policies.
- [ ] 3.4 Implement artifact explorer with diff visualisations, signature status, readiness gates, license-aware downloads, hash verification before download, and download audit logging.
- [ ] 3.5 Implement user preference management (theme, language, saved filters, default workspace) with persistence, policy enforcement, and audit of preference changes.
- [ ] 3.6 Integrate notification center with governance/readiness telemetry (`GovernanceTelemetry.readiness_notifications()`), prompt pack alerts, acknowledgement/snooze workflows, and audit logging.
- [ ] 3.7 Implement offline-aware action queueing for key workflows (waiver approvals, job submissions) with retry and conflict resolution messaging.
- [ ] 3.8 Document onboarding guide (`docs/gui/getting_started.md`) covering setup, local dev, auth configuration, feature flag usage, accessibility practices, troubleshooting, and compliance/residency guidance.

## 4. Testing & Validation

- [ ] 4.1 Create component/unit/integration tests with mock services, including accessibility checks (WCAG 2.1 AA), localization toggles, session security coverage, command palette workflows, offline queue scenarios, and download hash verification.
- [ ] 4.2 Run end-to-end tests against staging backend to confirm parity with CLI workflows, readiness pipelines, notification feeds, and preference persistence; capture test plan results.
- [ ] 4.3 Conduct security & performance review (OWASP, MFA flows, load testing, CSP) and address findings, including data residency and retention compliance checks.
- [ ] 4.4 Execute `openspec validate add-gui-foundation --strict`.
