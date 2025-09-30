## ADDED Requirements

### Requirement: GUI Shell & Navigation
The system SHALL provide a browser-based GUI shell with authentication, RBAC-aware navigation, tenant/project switching, global search, contextual help, command palette, and user preference management, eliminating the need for CLI invocation for supported workflows.

#### Scenario: Authenticated user accesses dashboard
- **WHEN** an operator with valid credentials visits the GUI
- **THEN** the GUI SHALL authenticate via existing service auth (JWT/mTLS/OIDC), present navigation limited to their roles, load contextual help, honor user preferences (theme, default workspace), and surface the global dashboard.

#### Scenario: Tenant context switch
- **WHEN** a user selects a different tenant/project context within the GUI
- **THEN** the GUI SHALL rehydrate state (artifact lists, jobs, metrics) scoped to the chosen context, update breadcrumbs/navigation, reset relevant filters, and log the context change with audit metadata including actor, tenant, and reason.

#### Scenario: Global search and command palette
- **WHEN** a user invokes the command palette or global search
- **THEN** the GUI SHALL surface quick actions (navigate to workspace, run job, open artifact, approve waiver), filtered by RBAC and context, supporting fuzzy search and keyboard navigation, executing the selected action without CLI calls.

### Requirement: Pipeline Overview Dashboard
The GUI SHALL render a real-time dashboard summarizing key DomainDetermine pipeline metrics (ingestion status, coverage health, mapping throughput, overlay backlog, prompt pack readiness, eval readiness, governance alerts, cost usage) with incident banners, drill-down links, saved views, and export options.

#### Scenario: Dashboard refresh without CLI
- **WHEN** a user opens or refreshes the dashboard
- **THEN** the GUI SHALL call backend APIs (with caching and streaming updates) to retrieve the latest metrics, display status cards with alerts, provide drill-down navigation to relevant workspace panels, and support exporting summaries to CSV/JSON without requiring CLI commands.

### Requirement: Artifact Lineage Explorer
The GUI SHALL provide an interactive artifact explorer to browse snapshots, coverage plans, mappings, overlays, prompt packs, readiness scorecards, eval suites, manifests, run bundles, and diff reports with lineage graphs, compare views, annotations, and license-aware export controls.

#### Scenario: View artifact lineage graph
- **WHEN** a user selects a coverage plan in the GUI
- **THEN** the GUI SHALL visualize upstream/downstream artifacts (KOS snapshot, overlay deltas, audit certificate, readiness report, eval suites), display metadata/diffs, annotate changes, enforce licensing policies (masking restricted labels), and offer direct downloads subject to RBAC and policy.

### Requirement: Notifications, Audit, and Inbox Center
The GUI SHALL include a notification center aggregating audit events, waivers, failing checks, pending approvals, job failures, cost overruns, prompt drift alerts, security incidents, policy expirations, and action items across tenants, with filtering, assignment, snooze, and mark-as-done capabilities.

#### Scenario: Operator reviews pending waivers
- **WHEN** audit logs indicate pending waivers
- **THEN** the GUI SHALL highlight the waivers in the inbox, allow drilling into context with supporting evidence, enable assignment/escalation, and provide action links to the appropriate module workspace for approval.

### Requirement: API Compatibility, Session, and Preference Management
The backend SHALL expose GUI-oriented endpoints (REST/GraphQL/websocket) and session middleware that encapsulate existing service operations (artifact CRUD, job status, telemetry, search, notifications) with pagination, caching, typed errors, retry semantics, CSRF protections, rate limiting, and user preference APIs.

#### Scenario: GUI retrieves job status stream
- **WHEN** the GUI requests logs for an ingestion job
- **THEN** the backend SHALL stream logs over websocket or chunked HTTP response, enforce RBAC/tenant filters, support pagination/replay, handle reconnects with backoff, and emit telemetry for the request.

#### Scenario: Persist user preferences
- **WHEN** a user updates GUI preferences (theme, columns, saved filters)
- **THEN** the backend SHALL persist preferences tied to user/tenant, validate inputs, enforce policy defaults, and return updated settings for immediate application.

### Requirement: Accessibility, Localization, Security, and Offline Resilience
The GUI SHALL meet WCAG 2.1 AA accessibility standards, support localization/internationalization for UI strings and date/number formats, enforce security controls (CSP, XSS/CSRF protection, MFA, session timeout, device posture, audit trails), implement offline-friendly messaging and action queueing, and expose compliance banners/license notices where required.

#### Scenario: Screen reader navigation
- **WHEN** a user navigates the GUI with a screen reader
- **THEN** the layout SHALL expose semantic landmarks, ARIA labels, keyboard focus management, skip links, and ensure all core workflows remain accessible, including command palette and modals.

#### Scenario: Session timeout handling
- **WHEN** a session exceeds inactivity threshold
- **THEN** the GUI SHALL warn the user, log out, prompt re-authentication (with MFA if applicable), and log the event with audit metadata including device/IP.

#### Scenario: Localization toggle
- **WHEN** a user switches UI language (where enabled)
- **THEN** the GUI SHALL update visible strings, date/number formatting, right-to-left support if necessary, and maintain navigation state without page reloads, persisting language preference.

#### Scenario: Offline action queue
- **WHEN** the GUI loses connectivity while the user performs an action (e.g., approve waiver)
- **THEN** the GUI SHALL queue the action locally, inform the user, retry submission when connectivity returns, avoid duplicate submissions, and log the event once successful or after giving resolution options.
