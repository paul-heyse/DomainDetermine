## MODIFIED Requirements
### Requirement: Baseline Quota Allocation Strategies
The coverage planner SHALL provide baseline quota allocation strategies including uniform allocation, proportional allocation by concept population or leaf count, Neyman allocation when variance estimates exist, and a cost-constrained allocation that MUST be solved via a deterministic linear-programming engine (e.g., PuLP or OR-Tools). Each plan MUST record which strategy was chosen, the inputs used, the solver configuration (objective, constraints, seed), and the resulting quotas before and after rounding. The planner SHALL expose deterministic rounding using a largest-remainder or equivalent method to ensure totals match the requested budget, MUST store any rounding deltas alongside the affected strata, and SHALL persist solver logs including convergence status, objective value, and any constraint relaxations. When the LP solver cannot produce a feasible allocation, the planner MUST emit a failure manifest, fall back to the previously certified allocation strategy, and record the reason in the allocation report.

#### Scenario: Records allocation metadata and rounding deltas
- **GIVEN** a requested total budget and a selected allocation strategy
- **WHEN** the planner computes quotas and applies deterministic rounding
- **THEN** the plan output records the strategy name, input statistics, pre-round quotas, post-round quotas, and per-stratum rounding deltas so totals match the requested budget

#### Scenario: Supports Neyman allocation when variance is available
- **GIVEN** stratum variance estimates from a pilot study
- **WHEN** the planner allocates quotas using the Neyman strategy
- **THEN** quotas are proportional to the variance-weighted size of each stratum and the plan metadata documents the variance source and timestamp

#### Scenario: Solves cost-constrained allocation via LP
- **GIVEN** per-stratum cost weights, risk weights, and fairness constraints
- **WHEN** the planner runs the cost-constrained strategy
- **THEN** it invokes a deterministic LP solver, records the objective and constraint set, captures solver logs, and stores the optimized quotas together with the solver’s convergence status

#### Scenario: Emits failure manifest and fallback when LP infeasible
- **GIVEN** the LP solver detects infeasibility for the cost-constrained strategy
- **WHEN** the planner cannot satisfy the constraints
- **THEN** it writes a failure manifest describing the violated constraints, reverts to the last certified allocation strategy, and annotates the allocation report with the fallback rationale
