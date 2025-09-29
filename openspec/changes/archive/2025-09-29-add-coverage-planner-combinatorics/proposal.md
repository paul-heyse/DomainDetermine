## Why
Baseline coverage planning needs explicit handling for combinatorial facet explosions and embedded business guardrails so that resulting plans remain tractable and policy compliant.

## What Changes
- Add requirements for pairwise and t-wise combinatorial coverage generation with traceability metadata.
- Define business guardrails that enforce policy filters, prevalence mixing, and risk-weighted allocations.

## Impact
- Affected specs: coverage-planner
- Affected code: Coverage Planner combinatorial generator, policy filter pipeline
