## ADDED Requirements
### Requirement: Overlay Namespace Governance
The system SHALL maintain overlay concepts in a dedicated namespace that references, but never overwrites, authoritative KOS nodes via `skos:broader`, `skos:narrower`, and match properties.

#### Scenario: Overlay node references base concept
- **WHEN** a new overlay node is approved for publication
- **THEN** the system SHALL persist a `skos:broader` link to its target base concept and record the base KOS snapshot identifier in the manifest

#### Scenario: Overlay avoids base identifier collision
- **WHEN** an overlay node is minted
- **THEN** the system SHALL assign an overlay-scoped identifier that is guaranteed not to collide with any licensed scheme identifier

### Requirement: Overlay Node Lifecycle
The system SHALL manage overlay nodes through states `candidate`, `approved`, `published`, and `deprecated`, recording reviewer identity, timestamps, and decision rationale for each transition.

#### Scenario: Reviewer approves node
- **WHEN** a reviewer marks an overlay node as approved
- **THEN** the system SHALL capture the reviewer ID, decision timestamp, and rationale, and move the node to the `approved` state

#### Scenario: Published node deprecation
- **WHEN** a published overlay node is deprecated
- **THEN** the system SHALL archive the node with a redirect target or deprecation note and emit a change log entry referencing impacted coverage strata

### Requirement: Overlay Node Data Model
The system SHALL store overlay nodes with preferred and alternate labels (per language), definitions, evidence pack references, difficulty bands, jurisdiction tags, provenance hashes, and links to Module 2 coverage strata.

#### Scenario: Persist evidence provenance
- **WHEN** an overlay node is saved in any state
- **THEN** the system SHALL record content hashes for the evidence pack, LLM prompt template, and base KOS snapshot to guarantee reproducibility

### Requirement: Overlay Integration with Modules
The system SHALL expose overlay nodes through Module 1 graph/tables as a distinct dataset and provide Module 2 with overlay-aware coverage plan deltas.

#### Scenario: Overlay node added to coverage planner
- **WHEN** an overlay node transitions to `published`
- **THEN** the system SHALL append a coverage plan delta row for Module 2 including initial quota guidance and provenance references

### Requirement: Overlay Quality Gates
Prior to human review, the system SHALL enforce automated quality gates covering duplicate/conflict scores, editorial policy compliance, licensing restrictions, and evidence presence.

#### Scenario: Duplicate score exceeds threshold
- **WHEN** a candidate overlay node exceeds the configured duplicate/conflict threshold with existing nodes
- **THEN** the system SHALL block progression to human review and surface the conflicting identifiers and similarity metrics

#### Scenario: Missing evidence pack
- **WHEN** a candidate overlay node lacks a valid evidence pack reference
- **THEN** the system SHALL mark the candidate as rejected with reason `MISSING_EVIDENCE` and prevent lifecycle advancement
