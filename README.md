# DomainDetermine

DomainDetermine translates high-level domain coverage requests into auditable data and evaluation blueprints. The codebase is organized around the workflow outlined in `AI-collaboration.md`:

1. **Module 1 – KOS Ingestion & Graph Service** (`src/DomainDetermine/kos_ingestion/`): fetch, normalize, and snapshot authoritative Knowledge Organisation Systems (KOS) into graph + tabular artefacts.
2. **Module 2 – Coverage Planner & Sampler** (`src/DomainDetermine/coverage_planner/`): combine curated concept frames, facets, and business constraints into versioned coverage plans with quotas.
3. **Module 3 – Mapping & Crosswalks** (`src/DomainDetermine/mapping/`): align free-text topics with concept IDs, track decisions, and emit evidence.
4. **Module 4 – Overlay Curation** (`src/DomainDetermine/overlay/`): propose and govern curated extensions layered on top of the base KOS.
7. **Module 7 – Governance & Versioning** (`src/DomainDetermine/governance/`): registry services for versioning, event logging, RBAC, backups, and diff tooling. Event signing requires providing a secret via `GovernanceEventLog(secret="…")` or the `GOVERNANCE_EVENT_SECRET` environment variable before publishes.

> The remaining modules described in the handbook (auditing, evals, governance, etc.) will live in future packages. Missing functionality is noted in `docs/architecture.md` under "Gaps vs. Handbook".

## Getting Started

```bash
# Run unit tests (requires local dependencies per environment.yml)
pytest -q

# Lint and format (ruff + black)
ruff check src tests
black .
```

## Key Concepts

- **KOS Snapshot** – Graph plus Parquet tables pinned to upstream source metadata.
- **Coverage Plan** – Deterministic stratification + quota allocation record used for task sampling and eval design.
- **Mapping Record** – Evidence-backed alignment between free text and canonical concepts.
- **Overlay Proposal** – Reviewer-approved extension to close coverage gaps without mutating the source KOS.

For a deeper narrative walkthrough, see `docs/architecture.md` and the per-module guides in `docs/`.
