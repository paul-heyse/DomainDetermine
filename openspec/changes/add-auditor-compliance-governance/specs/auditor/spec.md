## ADDED Requirements
### Requirement: Policy Compliance Validation
The coverage auditor SHALL enforce policy packs covering forbidden concepts, jurisdictional restrictions, licensing rules, and PII/PHI handling before approving a Coverage Plan.

#### Scenario: Forbidden concept detected
- **WHEN** a Coverage Plan row contains a concept flagged as forbidden by the policy pack
- **THEN** the auditor SHALL register a blocking failure with reason `FORBIDDEN_CONCEPT` and prevent certification

#### Scenario: Licensing restriction enforced
- **WHEN** the KOS license prohibits exporting full definitions
- **THEN** the auditor SHALL ensure audit outputs redact restricted fields and mark the certificate with licensing compliance status

### Requirement: Jurisdictional Validation
The auditor SHALL verify that jurisdiction-scoped slices comply with region-specific constraints, including prohibiting cross-region leakage.

#### Scenario: Jurisdiction mismatch
- **WHEN** a stratum tagged as `US-only` references EU-specific content
- **THEN** the auditor SHALL flag a blocking compliance failure with rationale `JURISDICTION_MISMATCH`

### Requirement: Drift Analysis Reporting
The coverage auditor SHALL compare the current Coverage Plan against a baseline, summarizing added/removed concepts, quota deltas, allocation method changes, and fairness metric drift.

#### Scenario: Drift summary generated
- **WHEN** a baseline Coverage Plan is provided
- **THEN** the auditor SHALL include a drift summary table in the audit dataset and annotate the report with primary drivers (policy, overlay, cost)

### Requirement: Waiver Workflow Integration
The system SHALL support waiver approvals for advisory or blocking gates, capturing approver identity, waiver reason, expiration, and linkage to policy references.

#### Scenario: Waiver recorded
- **WHEN** a waiver is granted for an advisory finding
- **THEN** the auditor SHALL persist the waiver details in the audit manifest and certificate, marking the affected metric as `WAIVED`

### Requirement: Governance Audit Trail
The coverage auditor SHALL record policy pack version, compliance reviewer identity, decision timestamps, and final approval status in all published artifacts.

#### Scenario: Governance metadata embedded
- **WHEN** the certificate is finalized
- **THEN** it SHALL include governance metadata fields for policy_pack_version, reviewer_id, approval_timestamp, and waiver_ids
