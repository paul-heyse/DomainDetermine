# coverage-planner Specification

## Purpose
TBD - created by archiving change add-coverage-planner-foundation. Update Purpose after archive.
## Requirements
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

### Requirement: Combinatorial Facet Coverage
The coverage planner SHALL detect when facet combinations create an intractable number of strata and MUST apply category-partition modeling to generate a minimal set of combinations that provide pairwise or configurable t-wise coverage. The planner SHALL reject invalid facet pairs during generation and MUST tag each emitted combination with the facet pairs or triples it covers so auditors can verify completeness.

#### Scenario: Generates minimal pairwise combinations
- **GIVEN** a facet grid whose Cartesian product would exceed the configured maximum strata
- **WHEN** the planner executes the combinatorial generator
- **THEN** the output includes a reduced set of strata that still covers every valid pair of facet values and records the coverage certificate for each generated combination

#### Scenario: Enforces invalid pair constraints
- **GIVEN** facet values that the policy layer marks as mutually exclusive
- **WHEN** the combinatorial generator evaluates candidate combinations
- **THEN** the generator skips those invalid pairs and documents the exclusion in the audit log

### Requirement: Coverage Planner Business Guardrails
The coverage planner SHALL enforce policy filters that remove forbidden, deprecated, or license-restricted concepts and SHALL route them to a quarantined list with rationale. The planner MUST support quota mixing that blends observed prevalence with uniform allocation using a documented mixing parameter, and it SHALL allow explicit risk weighting that increases quotas for high-impact strata while recording the justification.

#### Scenario: Routes forbidden strata to quarantine
- **GIVEN** a set of concepts flagged as forbidden or license restricted
- **WHEN** the planner assembles the coverage plan
- **THEN** the affected strata are excluded from allocation, added to a quarantine list, and annotated with the policy reason code

#### Scenario: Applies prevalence mixing with documented weights
- **GIVEN** observed prevalence data and a configured uniform-to-prevalence mixing parameter
- **WHEN** the planner allocates quotas
- **THEN** the resulting quotas reflect the blended distribution, and the plan metadata records the parameter value, prevalence snapshot, and rationale for any risk-weighted boosts

### Requirement: LLM-Assisted Refinement Controls
The coverage planner MAY use LLMs to suggest difficulty bands or missing subtopics, but every suggestion MUST be grounded in the canonical concept graph, supply citations, and receive human approval before altering strata membership or difficulty labels. The planner SHALL automatically reject LLM outputs that reference unknown concept IDs or violate policy filters and MUST log all accepted and rejected proposals with reviewer identities.

#### Scenario: Human approval gate for LLM proposals
- **GIVEN** an LLM-generated suggestion to adjust the difficulty band of a concept
- **WHEN** the suggestion references the canonical graph with supporting definition citations
- **AND** a reviewer approves the change
- **THEN** the planner applies the adjustment, records the reviewer identity, and stores the LLM prompt, response, and approval timestamp in the audit log

#### Scenario: Rejects invalid LLM suggestion automatically
- **GIVEN** an LLM-generated subtopic that references an unknown concept ID
- **WHEN** the planner validates the suggestion against the canonical graph
- **THEN** the suggestion is rejected, logged with the validation failure reason, and marked for optional reviewer follow-up

### Requirement: Coverage Plan Output Artifacts
The coverage planner SHALL emit a columnar coverage plan table containing concept identifiers, source information, path-to-root, depth, preferred and localized labels, facet assignments, quotas, minimums, maximums, allocation methods, rounding deltas, policy flags, risk tiers, cost weights, provenance, and solver logs. The planner SHALL provide an accompanying data dictionary that documents every column and allowed values, and it MUST produce an allocation report that explains the chosen strategy, fairness constraints, and deviations from proportionality.

#### Scenario: Emits coverage plan table with provenance
- **GIVEN** a completed allocation run
- **WHEN** the planner writes outputs
- **THEN** the columnar table includes all required identifier, facet, quota, control, and provenance columns, and the manifest references the KOS snapshot ID and allocation strategy version

#### Scenario: Publishes data dictionary and allocation report
- **GIVEN** the plan output table
- **WHEN** artifacts are finalized
- **THEN** the planner produces a data dictionary describing each column and an allocation report that justifies fairness settings and highlights deviations from proportionality

### Requirement: Coverage Plan Auditing and Diagnostics
The coverage planner SHALL calculate coverage health metrics including quotas by depth, by branch, by facet, percentage of leaves covered, entropy, and Gini coefficient. The planner MUST flag red conditions such as zero-quota strata, branches below policy thresholds, orphaned concepts without quota or exclusion reason, and high concentration in few branches. The planner SHOULD expose interactive what-if tooling that recalculates quotas when budget, mixing parameters, or fairness constraints change.

#### Scenario: Flags red conditions in audit report
- **GIVEN** a plan where a branch falls below its minimum threshold
- **WHEN** the audit diagnostics run
- **THEN** the resulting report highlights the branch as a red flag with the policy reference and suggests corrective actions

#### Scenario: Supports interactive what-if analysis
- **GIVEN** a stakeholder adjusts the total budget and mixing parameter in the what-if interface
- **WHEN** the planner recomputes quotas
- **THEN** updated allocations are produced immediately with clear diff highlights and recorded as an exploratory run

### Requirement: Coverage Plan Governance and Quality Standards
The coverage planner SHALL version each plan using semantic versioning tied to its KOS snapshot ID and MUST retain the last N versions for rollback. Diff reports SHALL enumerate added or removed concepts, quota deltas by branch, allocation method changes, and provide human-readable changelog entries. The planner MUST capture reviewer approvals with supporting evidence, support atomic rollback of the plan and snapshot pair, operate on columnar data stores for performance, and meet the defined SLOs for large ontologies. The planner SHALL include unit, property-based, and golden report tests to validate allocation determinism, constraint enforcement, combinatorial coverage, and diff readability.

#### Scenario: Produces diff and changelog for new version
- **GIVEN** a plan update that increases quotas for a policy-sensitive branch
- **WHEN** the planner publishes the new version
- **THEN** the diff report highlights the quota change, the changelog cites the pilot evidence, and the version metadata ties back to the KOS snapshot ID

#### Scenario: Executes rollback with paired snapshot
- **GIVEN** a regression detected after publishing a plan revision
- **WHEN** the operator triggers a rollback
- **THEN** the planner restores the previous plan version and associated KOS snapshot in one operation and records the rollback in the governance registry

#### Scenario: Enforces testing standards during release
- **GIVEN** a release candidate plan
- **WHEN** the testing pipeline runs
- **THEN** unit, property-based, and golden report tests pass, confirming deterministic allocation, valid combinatorial coverage, and stable diff output before approval is granted

