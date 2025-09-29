## ADDED Requirements
### Requirement: Overlay Reviewer Workbench
The system SHALL provide reviewers with a workbench that displays proposal metadata, evidence quotes with citations, sibling context, and nearest-neighbor similarity scores.

#### Scenario: Reviewer triages proposal
- **WHEN** a reviewer opens a candidate in the workbench
- **THEN** the UI SHALL present the proposal summary, evidence snippets with citations, sibling list, and similarity diagnostics within 2 seconds

### Requirement: Overlay Decision Logging
The system SHALL capture accept/revise/reject decisions with reason codes, reviewer identity, timestamps, and optional notes, updating overlay node state transitions.

#### Scenario: Reviewer issues revision request
- **WHEN** a reviewer selects `REVISE`
- **THEN** the system SHALL move the node back to the candidate queue, record the revision rationale, and notify the proposal pipeline to regenerate with reviewer feedback

### Requirement: Overlay Pilot Annotation
The system SHALL run pilot annotations of 10–30 real items per accepted candidate, measuring inter-annotator agreement (IAA) and time-on-task before publication.

#### Scenario: Pilot fails annotatability threshold
- **WHEN** the pilot IAA or throughput falls below configured thresholds
- **THEN** the system SHALL demote the node to `candidate` with reason `PILOT_FAIL` and attach pilot statistics for reviewer follow-up

### Requirement: Overlay Split Merge Operations
The system SHALL support reviewer-approved split and merge operations with migration instructions for existing mappings and coverage plan adjustments.

#### Scenario: Reviewer approves split
- **WHEN** a split decision is approved
- **THEN** the system SHALL create child overlay nodes, update Module 3 mapping migration guidance, and mark the parent as non-leaf with status `split`

### Requirement: Overlay Synonym Management
The system SHALL add reviewer-approved synonyms as `altLabel` entries with language tags while preventing collisions with existing labels in the base or overlay namespace.

#### Scenario: Synonym collision detected
- **WHEN** a proposed synonym matches an existing label in the same language
- **THEN** the system SHALL block the addition and prompt the reviewer to select a different synonym or map to the existing node

### Requirement: Overlay Coverage Feedback Loop
The system SHALL push accepted overlay nodes and associated pilot metrics to Module 2, updating coverage plan quotas and documenting the change in the overlay manifest.

#### Scenario: Accepted node updates coverage
- **WHEN** a node passes pilot and transitions to `published`
- **THEN** the system SHALL emit a coverage plan delta with updated quotas and append a manifest entry linking reviewer decisions and pilot metrics
