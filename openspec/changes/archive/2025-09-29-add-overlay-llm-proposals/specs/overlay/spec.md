## ADDED Requirements
### Requirement: Overlay Candidate Mining
The system SHALL mine candidate overlay concepts using corpus-driven keyphrase extraction and ontology analysis constrained by Module 2 coverage gap diagnostics and editorial policies.

#### Scenario: Corpus yields candidate phrase
- **WHEN** coverage diagnostics identify an under-covered branch
- **THEN** the candidate miner SHALL extract keyphrases from the linked corpus snippets using configured algorithms and emit normalized phrases with source document citations

#### Scenario: Ontology hole detection
- **WHEN** the ontology-driven analyzer finds a semantic cluster without a corresponding child node
- **THEN** the system SHALL record a candidate concept referencing the sibling cluster centroid and tag the source scheme used for justification

### Requirement: Overlay Retrieval-Augmented Prompting
The system SHALL construct retrieval-augmented prompt payloads that include parent definitions, sibling summaries, editorial rules, policy guardrails, and curated corpus excerpts before invoking an LLM.

#### Scenario: Prompt assembly for candidate generation
- **WHEN** an overlay gap enters the LLM generation queue
- **THEN** the system SHALL assemble a prompt bundle with the required context artifacts and record a content hash for reproducibility

### Requirement: Overlay LLM Structured Output
The LLM output SHALL conform to a strict JSON schema containing candidate labels, justifications with inline citations, annotation prompts, difficulty bands from a controlled vocabulary, and suggested nearest existing nodes.

#### Scenario: LLM returns invalid schema
- **WHEN** an LLM response fails schema validation or grammar constraints
- **THEN** the system SHALL discard the payload, log the failure, and retry with bounded attempts before flagging the candidate for manual review

### Requirement: Overlay Self-Critique and Policy Check
A secondary LLM critique pass SHALL evaluate overlap against existing nodes, annotatability, and verbatim policy compliance using the same evidence pack.

#### Scenario: Critique detects duplicate
- **WHEN** the critique identifies overlap above the configured threshold with another node
- **THEN** the system SHALL mark the candidate as `REJECTED_DUPLICATE` and attach the conflicting IDs and rationale to the audit record

### Requirement: Overlay Automated Vetting
The system SHALL run automated vetting covering duplicate/conflict detection (lexical + embedding), editorial linting, citation verification, graph sanity, and child-batch cardinality limits prior to human review.

#### Scenario: Citation missing in evidence pack
- **WHEN** a cited snippet is not present in the evidence pack offsets
- **THEN** the system SHALL fail vetting and flag the candidate with reason `INVALID_CITATION`

### Requirement: Overlay Split Merge Synonym Suggestions
The system SHALL capture split, merge, and synonym suggestions within structured candidate outputs, including migration guidance and proposed altLabels with language tags.

#### Scenario: Split recommendation generated
- **WHEN** the LLM proposes splitting an existing overlay node
- **THEN** the system SHALL record child candidates with migration notes linking to affected mappings and mark the parent for reviewer attention

#### Scenario: Synonym suggestion approved by vetting
- **WHEN** a synonym suggestion passes duplication and policy checks
- **THEN** the system SHALL attach it as an `altLabel` candidate with the appropriate language code for reviewer confirmation
