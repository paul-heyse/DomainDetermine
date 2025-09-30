## Why
The GUI requires dedicated backend support to expose workspace-oriented APIs, streaming endpoints, search indices, notification feeds, and preference stores while aligning with existing DomainDetermine services. Without a consolidated backend change, each module would introduce ad-hoc endpoints that diverge from governance, security, and observability standards.

## What Changes
- Extend the service layer to provide GUI-optimized APIs (REST/GraphQL/websocket) for artifacts, jobs, notifications, search, user preferences, and global metrics, reusing existing domain logic.
- Introduce background services for notification fan-out, real-time subscriptions, and search indexing across artifacts (coverage plans, mappings, overlays, prompt packs, readiness reports).
- Implement user preference storage, saved views, and inbox workflows with tenancy-aware persistence and policy enforcement.
- Provide governance-compliant audit logging, trace IDs, rate limiting, payload schemas, and streaming endpoints suitable for GUI consumption, including caching and pagination.
- Extend CI/CD, telemetry, and documentation for the service layer to support GUI usage patterns.

## Impact
- Affected specs: `service`, `governance`, `prompt-pack`, `readiness`, `mapping`, new `gui` backend capability.
- Affected code: `DomainDetermine.service` (new controllers, routers, schema), notification/event bus integrations, search indexing jobs, preference persistence, deployment scripts, documentation.
