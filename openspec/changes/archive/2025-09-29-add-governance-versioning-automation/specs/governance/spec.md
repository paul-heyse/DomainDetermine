## ADDED Requirements
### Requirement: Semantic Version Automation
The governance registry SHALL provide semantic version calculators per artifact class with explicit change reason codes. Publish workflows SHALL invoke the calculator, comparing declared impact to detected changes, and SHALL block publishes with incorrect version increments.

#### Scenario: Incorrect version bump blocked
- **WHEN** an artifact declares a minor version but includes breaking changes
- **THEN** the calculator SHALL flag the mismatch, fail the publish, and require the version to be updated to a major increment.

### Requirement: Canonical Hashing & Signing
Artifacts SHALL provide canonical serialisations for hashing, and publish workflows SHALL compute cryptographic hashes, verify signatures (Sigstore/GPG), and store verification metadata in the registry. Hash mismatches or signature failures SHALL block publication.

#### Scenario: Signature verification
- **WHEN** an artifact is published
- **THEN** the registry SHALL recompute the canonical hash, verify the signature, and reject the publish if verification fails, logging the error and alerting governance.

### Requirement: Lineage Graph Maintenance
The registry SHALL maintain an acyclic lineage graph for artifacts, capturing upstream and downstream relationships. Publish operations SHALL update the graph, and validation SHALL ensure no orphan nodes or hash mismatches exist.

#### Scenario: Lineage validation
- **WHEN** a new artifact version references upstream dependencies
- **THEN** the registry SHALL update the lineage graph and fail the publish if dependencies are missing, revoked, or produce cycles.

### Requirement: Waiver Lifecycle Management
Waivers SHALL include owner, justification, mitigation plan, expiry date, and associated artifacts. The registry SHALL track waiver status, alert on upcoming expiries, and block publishes relying on expired waivers.

#### Scenario: Waiver expiry alert
- **WHEN** a waiver is within seven days of expiry
- **THEN** the registry SHALL notify owners, update dashboards, and prevent new publishes from referencing the waiver unless renewed.
