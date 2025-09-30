## Why
Governance requires robust versioning so artifacts can be compared, rolled forward, or rolled back safely. We must encode semantic version policy, hash workflows, and upstream linkage enforcement to prevent silent regressions.

## What Changes
- Introduce semantic version assignment rules and automation for major/minor/patch increments across artifact types.
- Define content hashing normalization, manifest signing, and hash verification workflows in the registry.
- Require upstream dependency pinning with parent references and ensure publish actions validate dependency availability.
- Provide lineage graph generation hooks to visualize artifact ancestry and detect orphaned or stale references.

## Impact
- Affected specs: governance
- Affected code: versioning services, manifest generators, hash/signature utilities, lineage graph builder, publish validation pipeline
