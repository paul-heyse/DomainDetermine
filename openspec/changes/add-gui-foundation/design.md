# add-gui-foundation – Design

## Context

The foundation change establishes the shared GUI shell for DomainDetermine: authentication, navigation, dashboards, notifications, artifact explorer, and global preferences. It must align with the `add-gui-architecture` blueprint and remain Python-native, using the NiceGUI + FastAPI stack defined there. This document translates the foundational requirements into concrete architectural decisions, components, and validation steps.

## Goals

- Deliver a NiceGUI-based shell that authenticates users, enforces RBAC/tenant switching, and surfaces global navigation, command palette, and contextual help.
- Provide pipeline overview dashboards covering module health metrics, incidents, cost, and readiness, pulling data through FastAPI GUI adapters.
- Implement artifact lineage explorer with diff views, download auditing, and license enforcement.
- Create notification and inbox center aggregating governance, readiness, job, and cost events with acknowledgement/snooze capabilities.
- Establish preference management, localization, accessibility, security posture, and offline messaging patterns.

## Non-Goals

- Implementing module-specific workspaces (handled in later changes).
- Shipping final production styling; focus is on structure, contracts, and shared components.
- Defining external ticketing integrations beyond placeholders (handled in `add-gui-operations`).

## Technology Alignment

- **Frontend:** NiceGUI mounted on FastAPI (`src/DomainDetermine/gui/app.py`).
- **Styling:** Tailwind via NiceGUI plugin; theme variables defined in `gui/theme.py`.
- **State:** NiceGUI store + Redis cache for tenant-scoped data; offline queue via `sqlitedict`.
- **Routing:** NiceGUI `app.add_page` with dynamic RBAC gating.
- **Authentication:** FastAPI dependency injecting JWT, mTLS optional; NiceGUI session pulls user info from dependency.
- **Telemetry:** OpenTelemetry FastAPI middleware; NiceGUI actions instrumented via wrappers.

## Component Map

| Component | Description | Key Interactions |
| --- | --- | --- |
| `ShellLayout` | Base layout with header, sidebar, breadcrumb, command palette trigger, notification indicator | Reads tenant/user from session; toggles theme; exposes command palette modal |
| `DashboardView` | Overview cards for ingestion, coverage, mapping, overlay, readiness, prompt pack, governance, service, cost | Calls `/gui/dashboard` adapter; supports saved views, exports |
| `ArtifactExplorer` | Tree/table hybrid listing artifacts across modules with lineage graph, diff panel, download actions | Calls `/gui/artifacts/list`, `/gui/artifacts/{id}/lineage`; triggers download flow |
| `NotificationCenter` | Drawer displaying alert inbox with filters, ack/snooze, assignment | Subscribes to `/ws/gui/notifications/{tenant}`; posts ack/snooze commands |
| `CommandPalette` | Fuzzy search actions, artifacts, CLI copy features | Fetches `/gui/search` + local command list; respects RBAC |
| `PreferencePanel` | User settings (theme, language, saved filters, default workspace) | Calls `/gui/preferences` REST; interacts with NiceGUI store |
| `HelpPanel` | Contextual documentation, SOP links, runbooks | Static links to docs; integrates with existing Markdown crates |

## Data Flows

1. **Authentication**: Upon login, FastAPI middleware validates JWT/mTLS, sets session cookie. NiceGUI `before_request` hook loads user context into store.
2. **Tenant switch**: User selects tenant in header; event triggers REST call to `/gui/context/switch`, updates store, invalidates caches, logs audit event.
3. **Dashboard refresh**: NiceGUI scheduler pulls `/gui/dashboard` every 60s; websockets push immediate updates on event changes.
4. **Notification ingestion**: Websocket feed writes to local store; ack/snooze actions call REST endpoints and update store, propagate ack state.
5. **Artifact download**: Explorer requests manifest, prompts user; backend verifies hash/signature, logs download metadata via governance telemetry.

## Security & Compliance

- **Session security**: Idle timeout 15 min, absolute session 8 hours (configurable per tenant). MFA prompts triggered via existing service hooks.
- **Device posture**: Optionally require mTLS client cert for privileged actions; guard via FastAPI dependency.
- **Content Security Policy**: Serve NiceGUI over same domain; only allow approved CDN endpoints (Tailwind). Inline scripts hashed.
- **Audit logging**: All UI actions log actor, tenant, action, artifact (if applicable), status, latency, trace id.
- **Licensing enforcement**: Artifact explorer masks restricted labels/definitions when tenant license forbids; backend returns placeholder text plus reason.

## Localization & Accessibility

- UI strings stored in `gui/i18n/*.json`; default English with fallback.
- NiceGUI components configured with ARIA labels; test via screen reader simulation (NVDA/VoiceOver) and `pa11y` scans.
- Right-to-left support toggled by language metadata; Tailwind classes adapt layout.

## Offline & Resilience

- **Action queue**: Approvals/acknowledgements queued locally with idempotency key; retried on reconnect.
- **Status banners**: Shell shows connectivity status; offline actions aggregated for review.
- **Retry/backoff**: REST calls wrapped with exponential backoff (using `tenacity`) and error messaging.

## Testing Strategy

- **Unit tests**: Validate view composition (NiceGUI component tree) using snapshot testing (`gui/tests/test_shell.py`).
- **Contract tests**: Ensure REST adapters return expected payloads, enforce RBAC; import fixtures from `tests/fixtures/gui/`.
- **Websocket tests**: Simulate notification stream; check ack/snooze semantics.
- **Accessibility tests**: `pa11y` CLI for key pages; manual keyboard navigation checks.
- **Security review**: Checklist in `docs/gui/security_review.md` verifying session, CSRF, feature flag gating, data residency.

## Deliverables

- `gui/app.py`: NiceGUI entrypoint with shell layout and routes.
- `gui/components/*`: Modular components (Dashboard, Explorer, Notifications, Preferences).
- `gui/services/*`: Client wrappers for REST/websocket interactions.
- `tests/gui/*`: Unit & integration tests for shell features.
- Documentation updates: onboarding guide, security review notes, command palette usage.

## Open Questions

- Determine final storage for user preferences (Postgres vs. existing governance store). Current assumption: reuse governance metadata DB with new table.
- Evaluate caching strategy for artifact explorer (server-side prefetch vs. on-demand). Prototype both in implementation.
- Confirm pricing/usage data source for cost dashboard (governance telemetry vs. external billing API).
