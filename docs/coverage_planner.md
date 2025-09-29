# Coverage Planner Guide (Module 2)

The coverage planner transforms a vetted concept frame (from Module 1) plus facets and business constraints into an auditable coverage plan. This guide links the implementation to the requirements in `AI-collaboration.md` and highlights areas that need further development.

## Workflow Stages

1. **Policy Filtering** (`CoveragePlanner._filter_policy`) – Removes deprecated/forbidden concepts and records them in a quarantine ledger, satisfying the handbook requirement for policy filters and justification.
2. **Facet Generation** (`_generate_facet_grid`) – Chooses between full Cartesian expansion and pairwise reduction:
   - Uses configured `coverage_strength` and `max_combinations` to decide whether to call `generate_pairwise_combinations` or `expand_full_cartesian`.
   - Invalid facet pairs are enforced via `FacetConfig.invalid_combinations`.
3. **Difficulty & Risk Banding** (`_infer_difficulty`, `_infer_risk`, `_apply_llm_suggestions`) – Heuristic depth/fan-out banding with optional LLM-approved overrides (difficulty adjustments only, flagged for reviewer audit).
4. **Strata Construction** (`_build_strata`) – Emits `CoveragePlanRow` entries and the matching `StratumAllocationInput` records. Each row carries provenance (snapshot ID, deduplication key, timestamp) and cost/risk weights.
5. **Quota Allocation** (`allocate_quotas`) – Supports `uniform`, `proportional`, `neyman`, and `cost_constrained` strategies. Applies:
   - Deterministic largest-remainder rounding.
   - Branch minimums/maximums, fairness floor/ceiling translation to absolute counts, and per-stratum minimum quotas.
   - Prevalence mixing via `mixing_parameter`.
6. **Diagnostics & Outputs**:
   - `build_diagnostics` computes branch/depth/facet distributions, entropy, Gini, and red flags (zero quotas, fairness violations, orphaned concepts).
   - `CoveragePlan` aggregates rows, allocation metadata & report, solver failure manifolds, data dictionary, and governance-friendly version info.
   - Tree policy selection (leaves-only vs mixed) and coverage strength metadata are pinned in the plan manifest.

## Key Data Structures

- `ConceptFrameRecord`: Canonical unit of input with depth, ancestry, and policy tags.
- `FacetDefinition`/`FacetConfig`: Facet grids with invalid combination constraints.
- `ConstraintConfig`: Encodes totals, fairness policies, cost/risk weights, and provenance (snapshot ID, strategy version).
- `CoveragePlanRow`: Serialized row ready for Parquet export, linking concept, facets, quotas, risk tier, provenance, and solver logs.
- `CoveragePlanDiagnostics`: Audit report summarizing coverage health.
- `SolverFailureManifest`: Captures LP failure metadata plus fallback rationale.

## Differences from Handbook Expectations

| Requirement (Handbook) | Current Status | Notes |
| --- | --- | --- |
| Pairwise/t-wise generation with traceability | **Partial** | Pairwise generation implemented; traceability is stored as deduplication keys but not full pair coverage certificates yet. |
| Cost-constrained optimisation via LP solver | **Complete** | Deterministic PuLP optimisation with constraint logging and fallback manifest. |
| LLM-assisted subtopic proposals with human approval | **Missing** | Only difficulty overrides honour approved suggestions; no new stratum creation. |
| Interactive what-if analysis | **Placeholder** | `CoveragePlan.what_if_runs` reserved but there is no Streamlit/UI binding. |
| Governance registry & signed manifests | **Missing** | Version metadata captured, but manifest signing + diff storage not hooked up. |
| Solver logs & fairness rationale | **Complete** | Allocation metadata now stores solver status, objective, constraint slack, and fallback details. |

## Extending the Planner

- **LP-backed Allocation**: Replace `cost_constrained` heuristic with PuLP optimisation to maximise information gain subject to fairness and ceiling constraints.
- **Traceability Metadata**: Persist pair coverage certificates per facet combination for audit checks.
- **LLM Workflow**: Introduce structured review tasks for overlay proposals and integrate with Reviewer Workbench (Module 8).
- **What-if Harness**: Expose a small FastAPI/Streamlit surface that reuses `_build_strata` and `allocate_quotas` for scenario analysis.
