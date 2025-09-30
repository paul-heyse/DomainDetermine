## Why

The existing tooling requires operators to rely on CLI commands and raw manifests, limiting adoption, visibility, and human-in-the-loop workflows. A first-class GUI—implemented with FastAPI plus NiceGUI so we stay aligned with the existing codebase—is needed to surface the DomainDetermine pipeline end-to-end with guardrails, replacing ad-hoc scripts and reducing operational toil. The foundation must enforce governance, security, accessibility, observability, and parity with existing CLI/service behavior so subsequent modules can build on a stable, scalable surface that still lives in our Python ecosystem.

## What Changes

- Introduce a browser-based GUI framework under `src/DomainDetermine/gui/` built on FastAPI backend endpoints and NiceGUI components that wrap governance registry, job orchestration, artifact browsers, telemetry, notifications, and search with RBAC-aligned navigation, tenant isolation, and user preference management.
- Deliver dashboards that surface pipeline health, artifact lineage, outstanding actions, incident banners, cost telemetry, and saved views without invoking CLI, including drill-down, export, and automation hooks—implemented with reusable NiceGUI widgets within `src/DomainDetermine/gui/views/` to keep authoring in Python.
- Implement shared UI components (layout, theming, navigation, notifications, command palette, global search, contextual help, inbox, user settings, offline messaging) using Python-first component libraries housed under `src/DomainDetermine/gui/`, integrating with existing services and supporting localization, accessibility, and security policies.
- Establish API contracts, auth/session flows, caching policies, telemetry standards, error handling, and feature flag strategies between the Python GUI layer in `src/DomainDetermine/gui/` and backend services, including websocket fallback, offline resilience, and CLI parity.
- Define non-functional baselines (performance budgets, accessibility criteria, browser/device matrix, telemetry instrumentation standards, threat model) and update documentation for operators and reviewers, highlighting Python-native tooling choices for maintenance.
- Scaffold the `src/DomainDetermine/gui/` package that mounts NiceGUI on FastAPI with placeholder workspace registrations, health checks, and CLI entrypoints so downstream changes extend a working baseline rather than creating it ad hoc.

## Impact

- Affected specs: `service`, `governance`, `readiness`, `prompt-pack`, `gui` capability.
- Affected code: new `DomainDetermine.gui` package (NiceGUI app + FastAPI integration), updates to API services/streaming adapters, telemetry/logging integrations, security middleware, user preference storage, documentation/runbooks/onboarding materials.
