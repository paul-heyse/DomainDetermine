## Why
Stakeholders need transparent diffs to understand what changed between versions and to approve releases confidently. We must define diff strategies per artifact type, produce human- and machine-readable outputs, and integrate them into the governance workflow.

## What Changes
- Specify diff dimensions for KOS snapshots, Coverage Plans, mappings, overlays, eval suites, prompt pack, run bundles, and certificates.
- Require automated diff generation on every publish, storing artifacts alongside manifests for review and audit automation.
- Provide summarization rules (top N changes, metric deltas, cost deltas) and link diffs into the approval UI/CLI and governance registry.
- Establish baselines for diff quality (e.g., highlight major drifts vs minor noise) and ensure diffs trigger advisory/ blocking gates when thresholds exceeded.

## Impact
- Affected specs: governance
- Affected code: diff generation pipeline, summary renderers, registry storage for diffs, approval tooling, automation hooks
