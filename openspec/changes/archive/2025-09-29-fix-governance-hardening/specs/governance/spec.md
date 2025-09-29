## MODIFIED Requirements
### Requirement: Governance Event Log
The governance system SHALL maintain an append-only, cryptographically signed event log capturing proposals, approvals, waivers, publishes, rollbacks, and notifications, with each event referencing artifact IDs and hashes.

#### Scenario: Event appended on publish
- **WHEN** an artifact is published
- **THEN** the system SHALL write a signed event containing artifact ID, version, hash, approvals, and timestamp to the append-only log using a registry-configured signing secret; if the secret is missing, the system SHALL fail the operation

### Requirement: Backup and Disaster Recovery
The governance system SHALL replicate registry data and governed artifacts across regions, perform periodic integrity checks, and maintain replay recipes (environment manifests, container images) enabling restoration of run bundles and indexes.

#### Scenario: Disaster recovery drill
- **WHEN** a recovery drill is executed
- **THEN** the system SHALL restore the registry snapshot and associated artifacts within the defined RTO and validate artifact hashes against manifests by selecting the latest snapshot based on recorded timestamp, not identifier order

### Requirement: Artifact Diff Generation
The governance system SHALL generate structured diffs for every artifact publish, covering the predefined dimensions for KOS snapshots, Coverage Plans, mappings, overlay schemes, evaluation suites, prompt packs, run bundles, and certificates.

#### Scenario: Coverage Plan diff produced
- **WHEN** a new Coverage Plan version is published
- **THEN** the system SHALL compute a diff showing added/removed strata, quota deltas by branch/facet, and fairness metric deltas, storing the diff payload alongside the manifest, and SHALL sanitize artifact identifiers before using them in filesystem paths
