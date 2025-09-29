## Why
Module 4 requires a governed overlay layer so we can expand taxonomies without mutating the authoritative KOS. We currently lack lifecycle rules, manifests, and integration points, blocking downstream coverage improvements.

## What Changes
- Establish overlay namespace governance, including state machine (candidate → approved → published) and reviewer accountability.
- Define canonical overlay node data model with provenance, evidence pack references, and linkage back to base KOS snapshots.
- Specify integration with Module 1 storage (graph + tables) and Module 2 coverage planning to keep overlays versioned and diffable.
- Set pre-publication quality gates and policy guardrails for overlay content prior to human review.

## Impact
- Affected specs: overlay
- Affected code: overlay data model, manifests, governance registry interfaces, integration jobs for Modules 1–2
