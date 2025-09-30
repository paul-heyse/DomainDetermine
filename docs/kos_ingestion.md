# KOS Ingestion Guide (Module 1)

This guide explains how the ingestion stack corresponds to Module 1 of the handbook and how each component contributes to the snapshot artefact.

## Supported Sources & Tooling

Module 1 ingests heterogeneous KOS sources through a common toolbox. Each source
type maps to a dedicated parser and supporting libraries; install the runtime
dependencies in the project micromamba environment (`./.venv`).

| Source type | Expected formats | Core libraries | Notes |
| --- | --- | --- | --- |
| SKOS/RDF thesauri | Turtle (`.ttl`), RDF/XML (`.rdf`/`.xml`), JSON-LD (`.jsonld`) | `rdflib` | Parser auto-detects format when unspecified. Ensure namespace prefixes are declared for custom vocabularies. |
| OWL ontologies | OWL 2 DL (`.owl`) | `owlready2` | Loads imports transitively; materializes classes, object/data properties, individuals for downstream normalization. |
| OBO ontologies | OBO Graph / OBO v1 (`.obo`) | `pronto` | Dumps a JSON materialization used by the normalization stage; large ontologies benefit from local caching. |
| Remote SPARQL endpoints | parameterized query text | `SPARQLWrapper`, `httpx`, `tenacity` | Currently supported for read-only connectors; results flow through the same manifest/metadata surfaces. |

Additional tooling:

- **Checksums & delta detection** – `hashlib` usage is encapsulated by `fetchers.CheckedResponse`.
- **Storage outputs** – `pandas` + `pyarrow`/`duckdb` write Parquet tables for analytics.
- **Validation** – `pyshacl` (graph shapes) and `pandera` (tabular checks) plug into the validation layer during snapshot packaging.

## Canonical Concept Schema

Each concept is normalized into the structures defined in `DomainDetermine.kos_ingestion.canonical`:

- `ConceptRecord` — canonical/source identifiers, scheme, preferred label, optional definition, language, depth, leaf/deprecated flags, `path_to_root`, child/descendant counts, and provenance metadata (`source`, version, license, retrieval timestamp).
- `LabelRecord` — per-language preferred and alternate labels with kind metadata (pref/alt/acronym/etc.).
- `RelationRecord` — directed broader/narrower edges that preserve multiple inheritance.
- `MappingRecord` — cross-scheme alignments with mapping type and target identifiers.
- `SnapshotTables` — pandas DataFrames for concepts/labels/relations/mappings/paths, exposed to downstream components and persisted as Parquet.

## Snapshot Manifest Structure

`pipeline.IngestConnector` emits a manifest per run (`SnapshotInfo`) and companion metadata files, capturing:

- `snapshot_id` (content hash) and creation timestamp.
- Source descriptors (id, type, location) with licensing notes and policy flags.
- Table schemas + path hashes for `concepts`, `labels`, `relations`, `mappings`, `paths`.
- Graph exports (Turtle/OWL/OBO JSON) for semantic queries.
- Validation report payload combining SHACL + Pandera results and editorial diagnostics. Each report now includes a `severity` flag (`passed`, `needs_review`, or `blocker`) derived from structural checks so reviewers can triage snapshots quickly.
- Telemetry (fetch/normalize/validation durations, bytes downloaded, ingest start time) and license/export policy flags. ConnectorMetrics retains detailed timings per run for observability.
- Module 1 review metadata (reviewer, sign-off status, waiver references) sourced from `reviews.json` and embedded by `IngestConnector`.
- `run.json` – a lightweight run summary written alongside the manifest that records licence/export posture, validation severity, diagnostic counts, and a telemetry snapshot (start time + connector metrics) for readiness dashboards.
- Sample artefacts live under `docs/samples/kos_ingestion/` (`manifest_sample.json`, `run_summary.json`) and can be shared with reviewers to illustrate the governed surface.

## Query & Diagnostics APIs

Module 1 exposes a read surface for downstream planners and mapping tooling. The
API reads from the snapshot tables generated during ingest (`SnapshotTables`)
and augments the graph with indexes and caches.

### Core operations

- `get_concept(identifier: str)` – Retrieves canonical or source keyed concepts,
  then hydrates labels, mappings, and relation fan-out. Responses are cached so
  repeated lookups remain memory-only.
- `list_children` / `list_parents` / `list_siblings` – Traverses the graph using
  relation caches that respect multiple inheritance and pre-computed
  `path_to_root` metadata.
- `subtree(identifier, max_depth=None)` – Performs breadth-first traversal with
  subtree-level LRU caching and size guards to avoid unbounded fan-out.
- `search_labels(query, lang="en", limit=25, ...)` – Executes deterministic
  fuzzy matching via `rapidfuzz`, returning retrieval provenance (`fuzzy` vs
  `semantic`) and the `non_authoritative` flag when semantic fallbacks are used.
- `resolve_mappings(identifier, target_scheme=None)` – Surfaces cross-scheme
  alignments together with mapping type history and provenance.
- `sparql(query_text, source_version)` – Proxies read-only SPARQL queries with
  enforced allow-lists, timeouts, row limits, and cache entries keyed by
  `(endpoint, query, snapshot)`.

### Performance targets

| Operation | Cold target (p95) | Warm cache target | Notes |
| --- | --- | --- | --- |
| `get_concept` | ≤120 ms | ≤20 ms | Hydrates labels/mappings; warmed by concept cache. |
| `subtree` (≤500 nodes) | ≤250 ms | ≤40 ms | LRU keyed by `(concept, depth)`, aborts above configurable size. |
| `search_labels` | ≤150 ms | ≤35 ms | Includes fuzzy ranking and optional semantic fallback. |
| `sparql_query` | ≤2 s | ≤10 ms | Cold pass delegates to remote endpoint; warm pass served from TTL cache. |

### Caching & indexing

- **DuckDB views** – `concepts`, `labels`, `relations`, `mappings`, and `paths`
  tables stay registered in-process for analytics-grade joins.
- **Concept cache** – Hydrated concepts are memoized under canonical and source
  identifiers via an LRU bounded by `QueryConfig.concept_cache_size`.
- **Relation cache** – Broader/narrower adjacency lists reuse an LRU store to
  amortize fan-out calls and feed `list_*` helpers.
- **Subtree cache** – `(concept, depth)` keys reuse frozen traversals up to the
  configured subtree size limit.
- **Label search cache** – Fuzzy results are cached per `(query, lang, limit)`
  and store retrieval provenance; semantic fallbacks share the same entry while
  being marked non-authoritative.
- **Semantic index hooks** – Optional `SemanticLabelIndex` implementations can
  supply embedding-backed recall while preserving audit data in responses.
- **SPARQL cache** – Query+snapshot keyed responses honour TTL and record
  per-endpoint hit/miss metrics.

### Safeguards & telemetry

- Structured logs capture `event=query`, identifiers, cache disposition, result
  sizes, and execution time, enabling request-level traceability.
- `QueryMetrics` aggregates counters such as `query.get_concept.requests`,
  `cache.concept.hit/miss`, `query.search.semantic_requests`, and timing series
  for each API surface. SPARQL instrumentation records `sparql.cache_hit`,
  `sparql.cache_miss`, and error counts.
- The SPARQL gateway filters on allowed HTTP prefixes, forces read-only
  keywords, enforces TTL-based caching, and caps both rows and wall-clock time.
- Validation attaches SHACL/Pandera outcomes together with editorial
  diagnostics covering duplicate labels, conflicting mappings, definition length
  anomalies, and capitalization inconsistencies; reports live alongside snapshot
  manifests for reviewers.

## Data Flow

```
SourceConfig → Fetcher → Parser → NormalizationPipeline → SnapshotTables → SnapshotInfo
```

1. **Configuration** (`models.SourceConfig`) – Defines where to fetch a KOS (file path, HTTP URL, SPARQL endpoint) and enforces per-source licensing via `LicensingPolicy`.
2. **Fetching** (`fetchers.HttpFetcher`, `SparqlFetcher`) – Retrieves raw bytes, captures HTTP headers, and wraps them in `CheckedResponse` objects that include checksums and ETag/Last-Modified data for delta detection.
3. **Parsing** (`parsers.ParserFactory`) – Selects the appropriate parser for SKOS/OWL/OBO formats. Each parser returns a `ParserOutput` with stats and a temporary graph file reference.
4. **Normalisation** (`NormalizationPipeline`) – Harmonises concept identifiers, labels, and relationships into canonical tables (`SnapshotTables`). This is the hand-off point for Module 2.
5. **Snapshotting** (`pipeline.IngestConnector._persist_snapshot`) – Persists Parquet tables plus any graph exports and emits a manifest used by downstream modules to pin provenance.
6. **Metadata & Metrics** – `build_metadata` and `ConnectorMetrics` capture run metadata (license state, policy notes, byte counts, timing) for audit logs and SLO tracking.

## Policy & Compliance Hooks

- **Audit Outputs**: `metadata.json` (per-run manifest) plus `SnapshotInfo.validation_report` populated with SHACL (pyshacl), Pandera summaries, and editorial diagnostics for downstream review queues.
- **Review Manifest**: Module 1 reviewers maintain `reviews.json` (per-source status, reviewer, waivers); `IngestConnector` merges this into each run summary for governance sign-off and readiness dashboards.
- **Snapshot Summary**: `summary.json` aggregates review, validation, and telemetry to streamline readiness checks.
- **Telemetry Capture**: Ingest connectors record start times and expose fetch/normalize/validation durations via ConnectorMetrics for readiness dashboards.

## Gaps vs. Handbook

| Requirement | Current Status | Notes |
| --- | --- | --- |
| SHACL validation of snapshots | **Available** | `SnapshotInfo.validation_report` contains pyshacl + Pandera summaries.
| Graph traversal/search service | **Available** | `SnapshotQueryService` provides traversal helpers, cached subtrees, and a safeguarded SPARQL gateway.
| Vector search indices | **Partial** | Pluggable semantic fallback supported; embedding generation remains optional/non-authoritative.
| License-aware exports | **Partial** | Policies resolved, but masking/emission enforcement is manual.
| Editorial diagnostics | **Available** | Validation report now surfaces duplicate labels, mapping conflicts, length/capitalization flags, and a severity classification in the manifest and `run.json` summary.

## Extending Module 1

- Automate license-based masking/redaction before releasing snapshot exports.
- Promote semantic embedding generation to a managed workflow (still flagged non-authoritative in APIs).
- Stream `QueryMetrics` and validation diagnostics into long-term observability storage for trend analysis.
