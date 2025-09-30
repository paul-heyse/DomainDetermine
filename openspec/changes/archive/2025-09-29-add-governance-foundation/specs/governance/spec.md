## ADDED Requirements
### Requirement: Governance Registry Scope
The system SHALL maintain a governance registry that treats KOS snapshots, Coverage Plans, mapping/crosswalk outputs, overlay schemes, evaluation suites, prompt packs, run bundles, and signed certificates as first-class, versioned artifacts.

#### Scenario: Registry object creation
- **WHEN** a new governed artifact is produced
- **THEN** the registry SHALL assign a globally unique identifier within the appropriate namespace and record artifact type, semantic version, content hash, creator, and timestamp

### Requirement: Artifact Metadata Schema
The registry SHALL capture for every artifact a manifest containing upstream references (with IDs and hashes), policy pack hash, license tag, human-readable title, change reason code, reviewer approvals, waiver IDs, and environment fingerprint (runtime versions, container digests).

#### Scenario: Manifest stored with upstream pins
- **WHEN** an artifact is published
- **THEN** its manifest SHALL include references to all upstream artifact IDs and hashes (e.g., Coverage Plan → KOS snapshot) and persist the manifest as part of the registry record

### Requirement: Release Lifecycle Policy
The governance process SHALL enforce the stages propose, build, audit, approve, sign, publish for every governed artifact, with major changes requiring change-control board approval and minor/patch flows following a dual-review rule.

#### Scenario: Publish blocked without approvals
- **WHEN** an artifact reaches the publish step without recorded approvals for the required roles
- **THEN** the system SHALL block publication and surface the missing approvals

### Requirement: Versioning and Hash Validation
The registry SHALL apply semantic versioning (major/minor/patch) and compute normalized content hashes for each artifact, rejecting publishes when the declared hash and computed hash differ.

#### Scenario: Hash mismatch detected
- **WHEN** the computed content hash differs from the manifest hash during publish
- **THEN** the system SHALL reject the publish and log an integrity failure event

### Requirement: Waiver Governance
Waiver records SHALL include owner identity, justification, expiration date, mitigation plan, and linkage to specific advisories; waivers SHALL be audited before publication is allowed.

#### Scenario: Waiver expires
- **WHEN** a waiver reaches its expiration date prior to publish
- **THEN** the system SHALL invalidate the waiver and require a new approval or remediation before proceeding

### Requirement: Rollback and Recovery Controls
The governance registry SHALL support atomic rollbacks to the last green artifact, emit warnings to downstream artifacts when their upstream dependencies are rolled back, and retain replay recipes (environment manifests, container digests) for disaster recovery.

#### Scenario: Upstream rollback warning
- **WHEN** an upstream artifact referenced by a published run bundle is rolled back
- **THEN** the system SHALL record an event, notify the run bundle owners, and mark the run bundle status as `UPSTREAM_ROLLED_BACK`
