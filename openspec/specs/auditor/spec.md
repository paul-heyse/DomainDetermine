# auditor Specification

## Purpose
TBD - created by archiving change add-auditor-reporting. Update Purpose after archive.
## Requirements
### Requirement: Audit Report Generation
The coverage auditor SHALL generate a human-readable report containing an executive summary, methodology overview, findings, and appendices aligned with Module 5 guidance.

#### Scenario: Report includes executive summary
- **WHEN** an audit run completes
- **THEN** the system SHALL produce a report whose first section summarizes gate statuses (green/yellow/red) and top remediation actions

### Requirement: Visualization Integration
The system SHALL embed generated visual assets (charts, heatmaps, drift graphs) into the report bundle and reference them in the certificate metadata.

#### Scenario: Visual asset embedded
- **WHEN** fairness and compliance modules output charts
- **THEN** the report renderer SHALL include those assets in the findings section and list their paths in the artifact manifest

### Requirement: Observability Instrumentation
The coverage auditor SHALL emit structured logs and OpenTelemetry spans for each check, capturing metric names, values, thresholds, status, and context identifiers (plan_version, audit_run_id).

#### Scenario: Check telemetry emitted
- **WHEN** a structural check executes
- **THEN** the system SHALL create a telemetry span with attributes `metric_name`, `metric_value`, `threshold`, `status`, `plan_version`, and `audit_run_id`

### Requirement: Artifact Storage & Retention
Audit artifacts (dataset, certificate, report, visual assets) SHALL be stored under immutable, versioned paths with retention metadata and access controls respecting KOS licensing.

#### Scenario: Artifacts stored immutably
- **WHEN** audit artifacts are published
- **THEN** they SHALL be written to storage paths parameterized by kos_snapshot_id and plan_version with retention and ACL metadata attached

### Requirement: Governance Distribution
The coverage auditor SHALL notify the governance registry and configured subscribers with artifact locations, audit status, and summary metrics after completion.

#### Scenario: Governance notification sent
- **WHEN** the audit run finishes
- **THEN** the system SHALL publish a notification containing audit_run_id, artifact URIs, certificate status, and waiver summary to the governance registry

