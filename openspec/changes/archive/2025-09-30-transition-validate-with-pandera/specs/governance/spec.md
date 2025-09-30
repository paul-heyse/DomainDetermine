## MODIFIED Requirements

### Requirement: Governance Registry Scope

The system SHALL maintain a governance registry that treats KOS snapshots, Coverage Plans, mapping/crosswalk outputs, overlay schemes, evaluation suites, prompt packs, run bundles, and signed certificates as first-class, versioned artifacts validated with Pydantic models.

#### Scenario: Registry object creation

- **WHEN** a new governed artifact is produced
- **THEN** the registry SHALL assign a globally unique identifier within the appropriate namespace, record artifact type, semantic version, content hash, creator, timestamp, and validate the manifest against the appropriate Pydantic schema before persisting.

### Requirement: Artifact Metadata Schema

The registry SHALL capture for every artifact a manifest containing upstream references (with IDs and hashes), policy pack hash, license tag, human-readable title, change reason code, reviewer approvals, waiver IDs, and environment fingerprint (runtime versions, container digests), enforcing schema integrity with Pydantic models.

#### Scenario: Manifest stored with upstream pins

- **WHEN** an artifact is published
- **THEN** its manifest SHALL include references to all upstream artifact IDs and hashes (e.g., Coverage Plan → KOS snapshot), validate successfully via the manifest Pydantic schema, and persist the manifest as part of the registry record.
