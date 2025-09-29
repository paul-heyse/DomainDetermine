## ADDED Requirements
### Requirement: Canonical KOS Concept Model
The system SHALL represent every ingested concept using a canonical schema that includes stable identifiers, source metadata, multilingual labels, definitions, hierarchical relationships, and cross-scheme mappings.

#### Scenario: Concept normalization succeeds
- **WHEN** a concept is ingested from SKOS, OWL, or OBO
- **THEN** it SHALL be stored with a canonical identifier, preferred labels per language, alternative labels, definitions/scope notes where available, broader/narrower links, and provenance metadata capturing source, version, license, retrieval timestamp, and raw file hash.

#### Scenario: Provenance captured for each concept
- **WHEN** the ingest pipeline processes a concept record
- **THEN** the stored representation SHALL include source identifiers, source_version, ingest_timestamp, and license flags so downstream artifacts can pin to the originating snapshot.

### Requirement: Snapshot Packaging
The system SHALL emit each ingest run as a versioned snapshot containing both a graph store and columnar analytical tables, accompanied by a manifest.

#### Scenario: Snapshot manifest generated
- **WHEN** an ingest run completes successfully
- **THEN** the system SHALL write a manifest that records snapshot_id (content hash), source versions, file paths, table schemas, and license notes.

#### Scenario: Dual storage outputs produced
- **WHEN** an ingest run completes successfully
- **THEN** the system SHALL persist (a) an rdflib-backed graph store suitable for semantic queries and (b) Parquet/DuckDB tables named concepts, labels, relations, mappings, and optional paths.

### Requirement: Ingestion Observability and Validation
The system SHALL validate ingested data against structural rules and emit telemetry for monitoring.

#### Scenario: Structural validation enforced
- **WHEN** an ingest run loads data
- **THEN** the system SHALL execute SHACL shape checks and tabular integrity validations, failing the run if blocking errors (missing prefLabel, broken references, ID collisions) are detected.

#### Scenario: Telemetry captured for ingest
- **WHEN** an ingest run executes
- **THEN** the system SHALL emit structured logs and metrics covering parse counts, validation failures, graph size, snapshot duration, and cache hit ratios.

#### Scenario: Licensing policies applied
- **WHEN** an ingest run processes a source with export restrictions
- **THEN** the manifest SHALL record the license policy, and the system SHALL honor configuration that blocks export of restricted labels or mappings while allowing derived statistics.
