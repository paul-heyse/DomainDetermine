## Why
Module 6 requires explicit guidance on suite scaffolding, slicing, and item stability so evaluation suites remain consistent and auditable across releases.

## What Changes
- Define composition rules for scenarios, slices, and quota-respecting item allocation.
- Document item provenance strategies (static vs semi-dynamic) and sampling controls.
- Establish cross-suite consistency expectations to avoid concept leakage and maintain metric comparability.

## Impact
- Affected specs: eval-blueprint
- Affected code: Suite composer, slice registry, item sampler, seed management utilities.
