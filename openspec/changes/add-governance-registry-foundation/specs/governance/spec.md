## ADDED Requirements
### Requirement: Registry Scope & Identifier Policy
The governance registry SHALL treat KOS snapshots, coverage plans, mapping outputs, overlay proposals, evaluation suites, prompt packs, readiness scorecards, run bundles, and certificates as first-class versioned artifacts. Each artifact SHALL receive a globally unique identifier formatted as `<artifact-class>/<tenant>/<slug>/<version>` and SHALL record namespace ownership.

#### Scenario: Artifact creation
- **WHEN** a new governed artifact is produced
- **THEN** the registry SHALL assign an ID, persist metadata (type, semantic version, hash, title, summary, upstream links, policy pack hash, license tags, approvals, waivers, environment fingerprint), and return a registry reference.

### Requirement: Manifest Schema Enforcement
All artifacts SHALL store manifests following the canonical schema capturing upstream references (IDs + hashes), policy packs, license tags, change reason codes, reviewer approvals, waiver IDs, and environment fingerprints. Partial manifests SHALL be rejected.

#### Scenario: Manifest validation failure
- **WHEN** a manifest omits required fields (e.g., upstream hash, license tag)
- **THEN** the registry SHALL reject the submission with a validation error.

### Requirement: Event Logging & Telemetry
Registry operations (create/update/publish/rollback/delete) SHALL emit structured events with trace IDs, actor, artifact ID/version, operation type, and outcome. Events SHALL integrate with observability pipelines and readiness dashboards.

#### Scenario: Publish event emitted
- **WHEN** an artifact is published
- **THEN** an event SHALL be emitted capturing artifact metadata, approvals, and upstream dependencies for audit trails.

### Requirement: Backup & Recovery
The registry SHALL support scheduled backups (minimum daily) with encrypted storage, restoration drills at least quarterly, and documented disaster recovery runbooks. Backups SHALL include manifests, events, and lineage data.

#### Scenario: Backup verification
- **WHEN** a backup completes
- **THEN** the system SHALL record backup metadata (timestamp, checksum, storage location) and run integrity checks, alerting if validation fails.

#### Scenario: Recovery drill
- **WHEN** a quarterly recovery drill is executed
- **THEN** operators SHALL restore a backup to a staging environment, verify artifact integrity, document outcomes, and store the report in the governance registry.
