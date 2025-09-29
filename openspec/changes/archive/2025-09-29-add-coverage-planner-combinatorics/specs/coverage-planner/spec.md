## ADDED Requirements
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
