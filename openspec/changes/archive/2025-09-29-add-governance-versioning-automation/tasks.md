## 1. Specification & Approval
- [x] 1.1 Document semantic version triggers, hashing/signature requirements, lineage graph policies, and waiver lifecycle expectations.
- [x] 1.2 Review with Module 7 governance owners.

## 2. Implementation
- [x] 2.1 Implement version calculators with change reason codes and integrate into publish workflow.
- [x] 2.2 Enforce signature verification and canonical hashing during publish.
- [x] 2.3 Generate lineage graphs (networkx) and validate for orphan nodes/hash mismatches.
- [x] 2.4 Build waiver lifecycle tooling (creation, expiry alerts, escalation).

## 3. Documentation & Observability
- [x] 3.1 Update governance docs/runbooks with versioning and waiver processes.
- [x] 3.2 Publish observability metrics/dashboards for versioning and waiver status.

## 4. Testing & Validation
- [x] 4.1 Expand versioning/waiver unit tests.
- [x] 4.2 Run `openspec validate add-governance-versioning-automation --strict`.
