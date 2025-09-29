## 1. Overlay Namespace & Lifecycle
- [x] 1.1 Draft overlay ID schema and state machine doc (candidate → approved → published, deprecated)
- [x] 1.2 Implement lifecycle registry endpoints and persistence model with reviewer attribution

## 2. Overlay Data Model
- [x] 2.1 Define pydantic models/tables for overlay nodes, evidence packs, and manifest records
- [x] 2.2 Emit content-addressed manifests that pin base KOS snapshots and evidence hashes

## 3. Module Integration
- [x] 3.1 Expose overlay namespace through Module 1 graph/tables as separate datasets with provenance
- [x] 3.2 Update Module 2 coverage planner to accept overlay nodes and adjust quotas deterministically

## 4. Quality Gates & Policies
- [x] 4.1 Encode pre-publication validation (duplicate/conflict checks, editorial linting)
- [x] 4.2 Wire policy guardrails (forbidden categories, licensing flags) into overlay workflows
