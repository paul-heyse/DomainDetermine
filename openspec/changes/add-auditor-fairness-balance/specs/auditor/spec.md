## ADDED Requirements
### Requirement: Fairness Metric Computation
The coverage auditor SHALL compute fairness metrics (quota share, entropy, Gini coefficient, Herfindahl-Hirschman Index) across configured branches and facets for every Coverage Plan.

#### Scenario: Fairness metrics calculated per branch
- **WHEN** the auditor processes a Coverage Plan
- **THEN** it SHALL aggregate quotas by top-level branch and compute share, entropy, Gini, and HHI values stored in the audit dataset

### Requirement: Policy Threshold Evaluation
The system SHALL compare computed fairness metrics against policy-defined floors and ceilings, producing blocking or advisory statuses with rationale codes.

#### Scenario: Branch share exceeds ceiling
- **WHEN** a branch quota share surpasses the configured maximum
- **THEN** the auditor SHALL mark the metric as a blocking failure with rationale `BRANCH_SHARE_CEILING_EXCEEDED`

### Requirement: Sparse Density Detection
The auditor SHALL detect sparse or saturated facet cells (e.g., locale × difficulty) and zero-quota leaves, flagging them as advisory findings with remediation guidance.

#### Scenario: Sparse facet cell flagged
- **WHEN** a facet combination receives less than the configured minimum quota density
- **THEN** the auditor SHALL create an advisory finding in the audit dataset with suggested remediation text

### Requirement: Fairness Visualization Artifacts
The coverage auditor SHALL generate heatmaps and summary visualizations representing quota distribution and fairness status for inclusion in the human-readable report.

#### Scenario: Heatmap attached to report
- **WHEN** fairness metrics are computed
- **THEN** the auditor SHALL render a heatmap image per configured facet pair and embed it in the report asset bundle with references in the certificate metadata

### Requirement: Report Fairness Summary
The human-readable report SHALL include a fairness summary section listing metric values, status badges (green/yellow/red), and policy notes for each evaluated metric.

#### Scenario: Fairness summary published
- **WHEN** the audit report is generated
- **THEN** it SHALL include a table summarizing fairness metrics with their statuses and policy owner information
