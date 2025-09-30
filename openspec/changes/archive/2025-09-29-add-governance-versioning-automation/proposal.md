## Why
Semantic version calculators, signing/hashing, lineage graphs, and waiver lifecycle logic are implemented but not governed, risking inconsistent artifact publishing.

## What Changes
- Specify semantic version rules, canonical hashing/signature validation, lineage graph maintenance, and waiver metadata/expiry policies.
- Implement calculators with change reason codes, integrate signing verification, and generate lineage graphs with validation.
- Standardise waiver lifecycle (creation, expiry, escalation) and observability.

## Impact
- Affected specs: `governance/spec.md`
- Affected code: `src/DomainDetermine/governance/{versioning,waivers}.py`
- Tests: `tests/test_governance_versioning.py`, `tests/test_governance_waivers.py`
