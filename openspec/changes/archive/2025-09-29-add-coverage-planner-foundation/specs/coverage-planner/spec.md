## ADDED Requirements
### Requirement: Coverage Planner Input Surface
The coverage planner SHALL accept a concept frame that includes IDs, preferred labels, ancestor paths, depth, leaf flags, deprecation flags, and inherited domain attributes exported from Module 1. The planner SHALL allow callers to supply facet definitions (locale, language, modality, product line, customer segment, time period, and policy tags) together with total budget, per-branch minimums, fairness goals, SLO targets, and per-stratum cost or effort weights. The planner SHALL enforce risk and safety rules by rejecting forbidden concepts, honoring jurisdictional exclusions, and recording audit requirements. The planner SHOULD accept optional historical distributions to inform allocation but MUST preserve provenance when such distributions are applied.

#### Scenario: Accepts annotated concept frame and facets
- **GIVEN** a concept frame containing IDs, labels, depth, path-to-root, leaf flags, deprecation flags, and domain attributes
- **AND** a set of facet definitions with policy tags and constraint inputs
- **WHEN** the planner is invoked to build a coverage plan
- **THEN** the planner ingests the concept frame, attaches the facet grid, applies constraints, and records provenance for each input source

#### Scenario: Rejects forbidden or deprecated strata
- **GIVEN** a concept frame that marks certain concepts as deprecated or forbidden
- **WHEN** the planner evaluates the frame against supplied risk rules
- **THEN** the planner excludes the forbidden concepts from downstream strata generation and logs the exclusion with justification

### Requirement: Coverage Stratification Engine
The coverage planner SHALL construct strata using an explicit key schema that at minimum combines concept branch identifiers, depth bands, and supplied facets such as locale and difficulty. The engine SHALL support tree policies that select either leaves only or mixed interior nodes, and it MUST document the chosen policy in plan metadata. When concepts participate in multiple branches (e.g., a DAG), the engine SHALL support multi-parent membership while preventing double counting via a deduplication policy. Difficulty bands SHALL be initialized using structural signals (depth, fan-out) and lexical cues (term rarity, compound terms) and MAY be refined later through calibrated human review.

#### Scenario: Builds strata with documented policies
- **GIVEN** a concept subtree and facet configuration
- **WHEN** the stratification engine generates strata
- **THEN** each stratum includes the concept branch identifier, depth band, and facet assignments, and the resulting plan metadata records whether leaves-only or mixed-node policy was applied

#### Scenario: Handles DAG membership without double counting
- **GIVEN** a concept that belongs to two parent branches
- **WHEN** the stratification engine assigns strata
- **THEN** the concept appears in each applicable stratum with a deduplication flag so quotas can be reconciled without double counting

### Requirement: Baseline Quota Allocation Strategies
The coverage planner SHALL provide baseline quota allocation strategies including uniform allocation, proportional allocation by concept population or leaf count, and Neyman allocation when variance estimates exist. Each plan MUST record which strategy was chosen, the inputs used, and the resulting quotas before and after rounding. The planner SHALL expose deterministic rounding using a largest-remainder or equivalent method to ensure totals match the requested budget, and it MUST store any rounding deltas alongside the affected strata.

#### Scenario: Records allocation metadata and rounding deltas
- **GIVEN** a requested total budget and a selected allocation strategy
- **WHEN** the planner computes quotas and applies deterministic rounding
- **THEN** the plan output records the strategy name, input statistics, pre-round quotas, post-round quotas, and per-stratum rounding deltas so totals match the requested budget

#### Scenario: Supports Neyman allocation when variance is available
- **GIVEN** stratum variance estimates from a pilot study
- **WHEN** the planner allocates quotas using the Neyman strategy
- **THEN** quotas are proportional to the variance-weighted size of each stratum and the plan metadata documents the variance source and timestamp
