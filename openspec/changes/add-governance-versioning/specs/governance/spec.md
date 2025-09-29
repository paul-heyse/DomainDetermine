## ADDED Requirements
### Requirement: Semantic Version Management
The system SHALL automatically assign semantic versions (major, minor, patch) to governed artifacts based on declared change impact rules and store both the declared version and the previous version in the registry.

#### Scenario: Version bump enforcement
- **WHEN** an artifact publish request is submitted with a version inconsistent with its change impact classification
- **THEN** the registry SHALL reject the publish and prompt for the correct semantic version increment

### Requirement: Canonical Hashing and Signing
Every artifact manifest SHALL include a canonical serialization of the artifact payload, a cryptographic hash, and a signature generated using the configured signing authority; publishes MUST recompute and compare hashes prior to acceptance.

#### Scenario: Hash verification on publish
- **WHEN** the registry receives a publish request
- **THEN** it SHALL recompute the artifact hash from canonical payload and compare it with the manifest hash before accepting the signature

### Requirement: Upstream Dependency Pinning
Published artifacts SHALL list all upstream artifact IDs and hashes, and the registry SHALL validate that each dependency exists and is in a publishable state (not rolled back or revoked).

#### Scenario: Missing dependency detected
- **WHEN** an artifact references an upstream ID that is absent or revoked
- **THEN** the registry SHALL block publication and log a dependency validation failure

### Requirement: Lineage Graph Maintenance
The governance system SHALL maintain an acyclic lineage graph showing parent-child relationships among artifacts and provide APIs to query ancestry, descendants, and impacted artifacts for a given node.

#### Scenario: Lineage query for rollback impact
- **WHEN** a rollback is requested
- **THEN** the system SHALL return the set of dependent artifacts (children) that will receive rollback warnings before the action is approved
