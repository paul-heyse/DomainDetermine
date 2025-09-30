## Why
A modular GUI requires deep integration with each DomainDetermine module (ingestion, coverage planner, mapping, overlay, auditor, evals, readiness, prompt pack, governance, service operations). By standardising on FastAPI + NiceGUI we can share code, data models, and deployment pipelines with the existing platform while exposing complex workflows, data contracts, and human-in-the-loop queues. Architectural planning is required to define workspace boundaries, data flows, consistency with services/CLI, and support observability, feature rollout, multi-tenant governance, and disaster recovery without leaving the Python ecosystem.

## What Changes
- Design dedicated GUI workspaces (modules 1–7, readiness, prompt pack, governance, service ops) using NiceGUI components ensuring CLI parity, module guardrails, SLAs, and audit checkpoints.
- Define backend orchestration, event streaming, state management, caching, search, and automation patterns for jobs, telemetry, artifacts, reviewer queues, prompt pack calibration, readiness gates, and release processes—implemented via FastAPI/redis/async Python services.
- Establish shared design system, layout primitives, data access policies, infrastructure components, feature flag controls, and extensibility model that rely on Python tooling (Jinja/Pydantic templates, plugin patterns) and handle RBAC, tenancy isolation, offline resilience, CLI interoperability, and tenant extensions.
- Describe data synchronization between the Python GUI layer, services, prompt pack runtime, readiness telemetry, governance registry, CLI automation, and external artifacts, including caching tiers, drift detection, idempotent mutations, schema versioning, and observability hooks.
- Enumerate security, observability, compliance, and extensibility constraints the architecture must satisfy (websocket fallbacks, streaming logs, manifest signatures, policy enforcement, automation integration) while staying within Python-native frameworks.
- Produce shared assets (NiceGUI skeleton under `src/DomainDetermine/gui/`, prototype modules, fixture datasets) that demonstrate the architecture and unblock usability/contract testing.

## Impact
- Affected specs: `kos-ingestion`, `coverage-planner`, `mapping`, `overlay`, `auditor`, `readiness`, `prompt-pack`, `service`, `governance`, new `gui` capability.
- Affected code: NiceGUI workspaces under `DomainDetermine.gui`, FastAPI adapters, search/index components, event bus integrations, prompt pack/readiness dashboards, CLI automation hooks, prototype modules, fixture datasets, documentation/design assets.
