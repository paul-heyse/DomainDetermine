## Why

- Mapping messy inputs to canonical concept IDs today is manual or ad-hoc, lacks auditability, and blocks downstream modules.
- Cross-scheme gaps (EuroVoc ↔ LKIF, FIBO ↔ JEL) prevent consistent analytics and coverage planning across domains.

## What Changes

- Introduce a standards-driven mapping & crosswalk capability that resolves free-text topics/spans into Module 1 concept IDs with evidence and calibrated confidence.
- Capture ranked candidate sets, LLM-gated rationales, and human adjudication signals for traceable review.
- Establish crosswalk proposal workflows with hybrid similarity + LLM justification and human approvals.
- Stand up governed storage, metrics, and human-in-the-loop operations to keep mappings immutable, versioned, and compliant.

## Impact

- Affected specs: mapping/mapping
- Affected code: mapping resolvers, candidate generation services, crosswalk pipeline, registry integrations, reviewer workbench surfaces, telemetry.
