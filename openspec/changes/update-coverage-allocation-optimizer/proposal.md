## Why
Documentation work highlighted that the coverage planner’s cost-constrained allocation diverges from the handbook: it uses heuristics instead of a linear-programming optimizer and does not emit solver logs for audit. We need to update the spec so future implementation work closes that gap.

## What Changes
- Require the cost-constrained allocation strategy to use an LP solver (e.g., PuLP/OR-Tools) with reproducible configuration.
- Mandate persistence of solver logs, convergence status, and fallbacks when the solver cannot find a feasible plan.
- Extend scenarios to cover audit expectations for solver output and deterministic fallback behaviour.

## Impact
- Affected specs: coverage-planner
- Affected code: Coverage planner allocation engine, logging/reporting hooks
