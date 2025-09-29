## Why
Module 2 of the DomainDetermine program needs a documented coverage planning capability so that downstream task generation and evaluation design can rely on a consistent, auditable plan. We want to capture how concept inputs, facets, constraints, and baseline allocation strategies work before implementation begins.

## What Changes
- Document the coverage planner input surface, including concept frames, facets, constraints, and policy hooks.
- Specify the stratification engine behavior for turning concept trees into strata keys and difficulty bands.
- Describe the base quota allocation strategies that every coverage plan must expose and record.

## Impact
- Affected specs: coverage-planner
- Affected code: Coverage Planner service, configuration loaders, allocation component
