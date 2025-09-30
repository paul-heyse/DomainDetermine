## MODIFIED Requirements
### Requirement: Canonical KOS Concept Model
The system SHALL represent every ingested concept using a canonical schema that includes stable identifiers, source metadata, multilingual labels, definitions, hierarchical relationships, and cross-scheme mappings. In addition, the system SHALL capture connector metadata and licensing policies for each source.

#### Scenario: Concept normalization succeeds
- **WHEN** a concept is ingested from SKOS, OWL, or OBO
- **THEN** it SHALL be stored with a canonical identifier, preferred labels per language, alternative labels, definitions/scope notes where available, broader/narrower links, provenance metadata (source, version, license, retrieval timestamp, raw file hash), and connector metadata (ingest method, endpoint URL or file path, checksum, fetch timestamp).

#### Scenario: Provenance captured for each concept
- **WHEN** the ingest pipeline processes a concept record
- **THEN** the stored representation SHALL include source identifiers, source_version, ingest_timestamp, license flags, connector metadata, and delta markers so downstream artifacts can pin to both the originating snapshot and connector configuration.

### Requirement: Ingestion Observability and Validation
The system SHALL validate ingested data against structural rules and emit telemetry for monitoring, including connector-level metrics.

#### Scenario: Structural validation enforced
- **WHEN** an ingest run loads data
- **THEN** the system SHALL execute SHACL shape checks and tabular integrity validations, failing the run if blocking errors (missing prefLabel, broken references, ID collisions) are detected.

#### Scenario: Telemetry captured for ingest
- **WHEN** an ingest run executes
- **THEN** the system SHALL emit structured logs and metrics covering parse counts, validation failures, graph size, snapshot duration, cache hit ratios, connector latency, retry counts, and delta detection outcomes.

#### Scenario: Licensing policies applied
- **WHEN** an ingest run processes a source with export restrictions
- **THEN** the manifest SHALL record the license policy, and the system SHALL honor configuration that blocks export of restricted labels or mappings while allowing derived statistics; connector telemetry SHALL record licensing policy enforcement events.

## ADDED Requirements
### Requirement: KOS Ingestion Connectors
The system SHALL provide connectors for supported KOS input sources with consistent fetch, validation, and licensing enforcement behaviors.

#### Scenario: SKOS/OWL/OBO file ingestion
- **WHEN** a user configures an ingest run with local or remote SKOS Turtle/RDF/XML/JSON-LD, OWL ontology, or OBO Graph file
- **THEN** the connector SHALL download (if remote) with checksum verification, parse using the designated library (rdflib, owlready2, pronto/obonet), record fetch metadata, and pass normalized triples/entities to the pipeline.

#### Scenario: SPARQL endpoint ingestion
- **WHEN** a user configures a read-only SPARQL source
- **THEN** the connector SHALL execute parameterized queries via SPARQLWrapper with throttling, caching, and result-size limits, recording connector telemetry and respecting per-endpoint authentication.

#### Scenario: Licensing guardrails enforced
- **WHEN** a connector downloads or queries a source with licensing restrictions
- **THEN** it SHALL populate per-source license metadata, enforce policy switches that restrict exporting raw labels/IDs, and surface violations as blocking errors.

#### Scenario: Delta detection via HTTP metadata
- **WHEN** a connector re-fetches a remote file
- **THEN** it SHALL use ETag/Last-Modified headers to detect changes, log delta status (unchanged/changed), and trigger downstream snapshot versioning when content changes.
