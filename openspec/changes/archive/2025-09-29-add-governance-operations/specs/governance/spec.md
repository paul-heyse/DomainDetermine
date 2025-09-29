## ADDED Requirements
### Requirement: Governance Event Log
The governance system SHALL maintain an append-only, cryptographically signed event log capturing proposals, approvals, waivers, publishes, rollbacks, and notifications, with each event referencing artifact IDs and hashes.

#### Scenario: Event appended on publish
- **WHEN** an artifact is published
- **THEN** the system SHALL write a signed event containing artifact ID, version, hash, approvals, and timestamp to the append-only log

### Requirement: Governance Observability
The registry SHALL emit telemetry for publication lead time, audit failure rate, rollback frequency, and registry latency, providing dashboards and alerts when SLOs are breached.

#### Scenario: Lead time alert triggered
- **WHEN** the rolling publication lead time exceeds the configured SLO
- **THEN** the governance telemetry SHALL fire an alert to maintainers with the affected artifact types and pending approvals

### Requirement: RBAC and Tenancy Enforcement
Access to governed artifacts SHALL be controlled via RBAC roles (creator, reviewer, approver, auditor, reader) and tenant isolation; cross-tenant references are forbidden unless explicitly authorized, and licensing tags MUST enforce redaction/masking policies on export.

#### Scenario: Unauthorized cross-tenant access
- **WHEN** a user attempts to access an artifact from another tenant without explicit share permission
- **THEN** the system SHALL deny the request and log a security event

### Requirement: Backup and Disaster Recovery
The governance system SHALL replicate registry data and governed artifacts across regions, perform periodic integrity checks, and maintain replay recipes (environment manifests, container images) enabling restoration of run bundles and indexes.

#### Scenario: Disaster recovery drill
- **WHEN** a recovery drill is executed
- **THEN** the system SHALL restore the registry snapshot and associated artifacts within the defined RTO and validate artifact hashes against manifests
