## Why
The GUI relies on backend services to deliver GUI-optimized APIs, streaming endpoints, search indices, notifications, and preference stores. To keep the stack cohesive, we will implement these capabilities in Python (FastAPI, Redis, Pydantic, Celery/ Dramatiq) and provide integration points that power the NiceGUI front end. Without a consolidated backend change, each module would introduce ad-hoc endpoints that diverge from governance, security, and observability standards.

## What Changes
- Extend the service layer (FastAPI/Pydantic) to provide GUI-optimized APIs (REST/GraphQL/websocket) for artifacts, jobs, notifications, search, user preferences, and global metrics, reusing existing Python domain logic.
- Introduce background services for notification fan-out, real-time subscriptions, and search indexing across artifacts, built with Python tooling (Celery/Dramatiq, Redis, Elastic/OpenSearch clients).
- Implement user preference storage, saved views, and inbox workflows with tenancy-aware persistence using Python ORM/NoSQL libraries.
- Provide governance-compliant audit logging, trace IDs, rate limiting, payload schemas, and streaming endpoints suitable for GUI consumption, including caching and pagination—all managed in Python.
- Extend CI/CD, telemetry, and documentation for the service layer to support GUI usage patterns within the Python environment.

## Impact
- Affected specs: `service`, `governance`, `prompt-pack`, `readiness`, `mapping`, new `gui` backend capability.
- Affected code: updates to `DomainDetermine.service` (FastAPI routers, Pydantic schemas), notification/event bus integrations (Redis/Kafka clients), search indexing jobs, preference persistence, deployment scripts, documentation.
