## MODIFIED Requirements

### Requirement: Snapshot Packaging

The system SHALL emit each ingest run as a versioned snapshot containing both a graph store and columnar analytical tables, accompanied by a manifest. The snapshot SHALL include precomputed traversal indexes to support query performance targets.

#### Scenario: Snapshot manifest generated

- **WHEN** an ingest run completes successfully
- **THEN** the system SHALL write a manifest that records snapshot_id (content hash), source versions, file paths, table schemas, license notes, and traversal index metadata (e.g., ancestor counts, leaf flags).

#### Scenario: Dual storage outputs produced

- **WHEN** an ingest run completes successfully
- **THEN** the system SHALL persist (a) an rdflib-backed graph store suitable for semantic queries and (b) Parquet/DuckDB tables named concepts, labels, relations, mappings, and optional paths with precomputed ancestor/descendant counts and leaf flags.

### Requirement: Ingestion Observability and Validation

The system SHALL validate ingested data against structural rules and emit telemetry for monitoring, including query-layer metrics.

#### Scenario: Structural validation enforced

- **WHEN** an ingest run loads data
- **THEN** the system SHALL execute SHACL shape checks and tabular integrity validations, failing the run if blocking errors (missing prefLabel, broken references, ID collisions) are detected.

#### Scenario: Telemetry captured for ingest

- **WHEN** an ingest run executes
- **THEN** the system SHALL emit structured logs and metrics covering parse counts, validation failures, graph size, snapshot duration, cache hit ratios, connector latency, retry counts, query latency, and SPARQL call statistics.

#### Scenario: Licensing policies applied

- **WHEN** an ingest run processes a source with export restrictions
- **THEN** the manifest SHALL record the license policy, and the system SHALL honor configuration that blocks export of restricted labels or mappings while allowing derived statistics; connector telemetry SHALL record licensing policy enforcement events.

## ADDED Requirements

### Requirement: KOS Query and Traversal APIs

The system SHALL expose read APIs that provide concept lookup, traversal, and search operations with defined performance guarantees and caching policies.

#### Scenario: Retrieve concept by identifier

- **WHEN** a client requests a concept by canonical identifier or source identifier
- **THEN** the API SHALL return labels, definitions, hierarchy links, mappings, provenance, and connector metadata from the snapshot.

#### Scenario: Traverse hierarchy efficiently

- **WHEN** a client requests children, parents, siblings, subtree, leaves, or path-to-root for a node
- **THEN** the API SHALL respond within configured latency targets using precomputed indexes or cached results, honoring multiple inheritance when present.

#### Scenario: Search by label or synonym

- **WHEN** a client searches by label, synonym, or normalized text with an optional language filter
- **THEN** the API SHALL perform fuzzy matching (rapidfuzz) with deterministic ranking, optionally invoking semantic embeddings marked non-authoritative and returning audit fields indicating retrieval method.

#### Scenario: Resolve cross-scheme mappings

- **WHEN** a client provides a concept identifier from scheme A and requests mappings to scheme B
- **THEN** the API SHALL return exactMatch/closeMatch results along with mapping provenance and drift versioning.

#### Scenario: Safe SPARQL gateway usage

- **WHEN** a client issues a SPARQL query through the gateway
- **THEN** the system SHALL enforce read-only patterns, apply query timeouts, limit result size, cache results keyed by query + source version, and log usage metrics.

### Requirement: Data Quality Diagnostics

The system SHALL enforce quality gates and provide diagnostics for editorial review.

#### Scenario: SHACL validation passes

- **WHEN** a snapshot is generated
- **THEN** the system SHALL run pyshacl validation against configured shapes (e.g., prefLabel presence, language tag conformance, DAG hierarchy) and block publication on failure.

#### Scenario: Tabular integrity checks succeed

- **WHEN** a snapshot is generated
- **THEN** the system SHALL run Pandera dataframe schemas verifying ID uniqueness, referential integrity, non-empty labels, and leaf flags, blocking publication if critical checks fail.

#### Scenario: Editorial diagnostics produced

- **WHEN** a snapshot is generated
- **THEN** the system SHALL output diagnostics for duplicate altLabels under a parent, conflicting mappings, suspicious definition lengths, and capitalization inconsistencies for editorial review; these SHALL be included in the manifest or accompanying report.
