## ADDED Requirements
### Requirement: Artifact Diff Generation
The governance system SHALL generate structured diffs for every artifact publish, covering the predefined dimensions for KOS snapshots, Coverage Plans, mappings, overlay schemes, evaluation suites, prompt packs, run bundles, and certificates.

#### Scenario: Coverage Plan diff produced
- **WHEN** a new Coverage Plan version is published
- **THEN** the system SHALL compute a diff showing added/removed strata, quota deltas by branch/facet, and fairness metric deltas, storing the diff payload alongside the manifest

### Requirement: Human-Readable Diff Summaries
For each diff, the system SHALL render a human-readable summary (markdown/HTML) highlighting the top changes, metric shifts, and policy impacts to support approver review.

#### Scenario: Summary attached to approval workflow
- **WHEN** approvers open a publish request
- **THEN** the UI/CLI SHALL display the associated diff summary with drift badges (green/yellow/red) based on configured thresholds

### Requirement: Machine-Readable Diff Schema
Diff outputs SHALL conform to a machine-readable schema (JSON) exposing change lists, metric deltas, and annotations so downstream automation can evaluate drift rules.

#### Scenario: Diff consumed by automation
- **WHEN** the audit automation queries the diff API
- **THEN** the system SHALL return a JSON payload that includes change categories, counts, metric deltas, and associated artifact IDs

### Requirement: Drift Threshold Alerts
The governance system SHALL evaluate diff metrics against configured thresholds and raise blocking or advisory alerts when exceeded, linking alerts to approval gates and waiver workflows.

#### Scenario: Drift threshold exceeded
- **WHEN** coverage branch share delta exceeds the configured limit
- **THEN** the system SHALL mark the diff status as `BLOCKING`, notify approvers, and require a waiver or remediation before publish can proceed
