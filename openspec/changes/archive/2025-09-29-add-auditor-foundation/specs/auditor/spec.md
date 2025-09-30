## ADDED Requirements
### Requirement: Coverage Auditor Capability Scope
The system SHALL provide a coverage auditor that validates Coverage Plans from Module 2 using authoritative concept data from Module 1 and emits signed audit artifacts tied to specific kos_snapshot_id and plan_version values.

#### Scenario: Audit run consumes plan and concept tables
- **WHEN** an audit run begins
- **THEN** the system SHALL load the Coverage Plan table along with Module 1 concept tables for the same kos_snapshot_id before executing any checks

#### Scenario: Audit artifacts link lineage
- **WHEN** the auditor emits outputs
- **THEN** each artifact SHALL record the kos_snapshot_id, plan_version, audit_run_id, and signing key identifier in its metadata

### Requirement: Structural Integrity Validation
The coverage auditor SHALL verify concept existence, deprecation status, referential integrity of path_to_root, unique identifiers, non-negative quotas, and facet vocabulary compliance for every stratum.

#### Scenario: Deprecated concept detected
- **WHEN** a Coverage Plan row references a concept marked deprecated in Module 1
- **THEN** the auditor SHALL flag the row as a blocking failure and record the concept_id in the audit dataset

#### Scenario: Invalid facet value
- **WHEN** a facet value does not belong to the declared domain for that facet
- **THEN** the auditor SHALL mark the stratum as failing structural validation with reason `INVALID_FACET_VALUE`

### Requirement: Audit Dataset Artifact
The coverage auditor SHALL produce a denormalized audit dataset capturing per-stratum metrics, structural statuses, fairness indicators, policy flags, and lineage metadata.

#### Scenario: Audit dataset persisted with lineage
- **WHEN** the audit dataset is written to storage
- **THEN** it SHALL be stored under an immutable path keyed by plan_version and include kos_snapshot_id and audit_run_id columns

### Requirement: Coverage Certificate Artifact
The coverage auditor SHALL generate a machine-readable coverage certificate containing pass/fail results, metric values, waiver references, and digital signatures.

#### Scenario: Certificate signing completed
- **WHEN** all checks finish and blocking gates pass
- **THEN** the system SHALL sign the certificate payload with the configured signing key and persist the signature alongside the certificate

### Requirement: Quality Gate Taxonomy
The coverage auditor SHALL classify checks into blocking and advisory gates, each with an owner role, threshold, and waiver controls recorded in the governance registry.

#### Scenario: Advisory gate warning recorded
- **WHEN** an advisory gate threshold is exceeded
- **THEN** the auditor SHALL record the warning, link the owning role, and mark the certificate status as `WARN` without blocking publication

### Requirement: Sign-Off Workflow
The coverage auditor SHALL capture sign-off events that include reviewer identity, timestamp, waiver list, and final status prior to publishing artifacts.

#### Scenario: Reviewer signs off with waiver
- **WHEN** a reviewer approves the plan with documented waivers
- **THEN** the system SHALL append the waivers and reviewer metadata to the certificate and audit manifest before publishing
