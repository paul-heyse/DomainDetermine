## Why
We need robust fairness and balance evaluations to ensure Coverage Plans meet quota distribution policies before execution. Without explicit metrics, thresholds, and visual diagnostics, stakeholders cannot trust plan equity or spot imbalances.

## What Changes
- Implement fairness metric engine computing branch/facet distributions (entropy, Gini, HHI, share vs. floors/ceilings) backed by DuckDB aggregations.
- Define heatmap visualizations and sparse-density detection for facet combinations to highlight gaps.
- Configure policy-driven thresholds with blocking/advisory outcomes and integrate results into audit dataset and certificate.
- Provide rationale annotations explaining metric failures and linking to policy packs.

## Impact
- Affected specs: auditor
- Affected code: fairness metric calculators, threshold evaluators, visualization generators, audit dataset enrichment, certificate writers
