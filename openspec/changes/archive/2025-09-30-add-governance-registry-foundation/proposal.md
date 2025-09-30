## Why
The governance registry, backup routines, and event logging exist but lack canonical requirements for artifact lifecycle, metadata schema, or disaster recovery, leaving Module 7 without enforceable guarantees.

## What Changes
- Define governance registry scope (artifact classes, ID format, manifest schema) and event logging expectations.
- Implement/confirm registry APIs, event log capture, and backup strategy; document recovery procedures.
- Integrate registry operations with readiness dashboards and governance observability.

## Impact
- Affected specs: `governance/spec.md`
- Affected code: `src/DomainDetermine/governance/{registry,backup,event_log,models}.py`
- Affected docs: Governance runbooks, readiness docs
- Tests: `tests/test_governance_registry.py`, backup/event log tests
