## ADDED Requirements
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
