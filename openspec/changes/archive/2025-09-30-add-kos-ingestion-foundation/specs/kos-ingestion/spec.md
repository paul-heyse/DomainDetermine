## ADDED Requirements
### Requirement: Canonical Concept Schema
The ingestion pipeline SHALL normalise all concepts to a canonical schema containing `concept_id`, `pref_label` (per language), `alt_labels`, `definition`, `scope_notes`, `broader`, `narrower`, `mappings` (exact/close/broad/narrow), provenance metadata (source system, version, license, retrieval timestamp, raw file hash), deprecation flags, and language codes.

#### Scenario: Concept normalisation
- **WHEN** a concept is ingested from SKOS, OWL, or OBO
- **THEN** the pipeline SHALL produce a canonical record with populated fields and record the provenance metadata for downstream pinning.

### Requirement: Snapshot Packaging
Each ingestion run SHALL emit a snapshot containing (a) an rdflib-backed graph store and (b) columnar tables (`concepts`, `labels`, `relations`, `mappings`, `paths`) stored as Parquet/DuckDB files, accompanied by a manifest referencing hashes and source versions.

#### Scenario: Snapshot manifest generated
- **WHEN** an ingest run completes successfully
- **THEN** the pipeline SHALL produce a manifest recording snapshot ID (content hash), source versions, file paths, table schemas, license notes, and store it in governed storage.

### Requirement: Validation & Quality Gates
Ingestion SHALL enforce SHACL shape validation on the graph, tabular integrity checks (unique IDs, referential integrity, language coverage), and SHALL block the run on critical failures. Warning-level issues SHALL be reported with remediation guidance.

#### Scenario: Validation failure stops pipeline
- **WHEN** SHACL validation finds missing mandatory labels
- **THEN** the pipeline SHALL halt, emit a failure report, and require remediation before snapshot publication.

### Requirement: Observability & Metrics
The ingestion pipeline SHALL emit structured logs and metrics covering parse counts, validation failures, graph size, snapshot duration, cache hit ratios, and license masking activity. Metrics SHALL be sent to readiness dashboards with snapshot IDs.

#### Scenario: Metrics exported per run
- **WHEN** an ingest run finishes
- **THEN** metrics SHALL record counts per concept, validation status, runtime, and resource usage, tagged with snapshot ID and source version.

### Requirement: License Enforcement & Masking
For sources with export restrictions, the pipeline SHALL mask restricted labels/definitions according to license policy, track license flags in manifests, and prevent downstream export of restricted fields unless explicitly allowed.

#### Scenario: License restriction applied
- **WHEN** a source prohibits exporting full labels
- **THEN** the pipeline SHALL mask labels in exported tables, record the masking rule in the manifest, and flag the restriction in the readiness dashboard.
