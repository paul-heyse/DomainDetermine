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

## Query & Diagnostics APIs

Module 1 exposes a read surface for downstream planners and mapping tooling. The
API reads from the snapshot tables generated during ingest (`SnapshotTables`)
and augments the graph with indexes and caches.

### Core operations

- `get_concept(identifier: str)` – Retrieve the canonical record by canonical or
  source identifier, including labels, definitions, relations, mappings,
  provenance, and validation metadata.
- `list_children(identifier, depth=1)` / `list_parents` / `list_siblings` –
  Traverse the directed graph using precomputed descendant/ancestor indexes; the
  service respects multiple inheritance and can return `path_to_root` data for
  audit.
- `subtree(identifier, max_depth=None)` – Materialize a subtree via breadth-first
  traversal, honoring cache TTLs for hot branches.
- `search_labels(query, lang="en", limit=25, fuzzy=True)` – Execute fuzzy label
  search using `rapidfuzz` over normalized label tables; optionally fall back to
  semantic embeddings (flagged `embeddings_non_authoritative=True`) for recall.
- `resolve_mappings(identifier, target_scheme=None)` – Return cross-scheme
  mappings with provenance (source, version, confidence).
- `sparql(query_text, source_id)` – Proxy read-only SPARQL queries with
  whitelisted patterns, enforced timeouts, row limits, and server-side caching
  keyed by `(query_text, source_version)`.

### Caching & indexing

- **DuckDB views** – `concepts`, `labels`, `relations`, `mappings`, `paths`
  tables are hydrated into an in-process DuckDB database for fast joins.
- **Fuzzy search index** – `rapidfuzz.process.cdist` or `rapidfuzz.process.extract`
  is used over normalized label text; results are cached per `(query, lang)`.
- **Hierarchy cache** – Frequent subtrees (configurable) are memoized in an LRU
  cache keyed by `(identifier, max_depth)`.
- **SPARQL cache** – Endpoint results cached in-memory with TTL; instrumentation
  records hit/miss ratios.

### Safeguards & telemetry

- Structured logs include `event: query`, `cursor`, `identifier`, `cache_hit`,
  `duration_ms`, `result_size`, and validation references.
- Metrics captured: `query.duration_seconds`, `cache.hit_ratio`,
  `sparql.latency_seconds`, `sparql.timeouts`, `search.requests`,
  `search.semantic_calls`.
- SPARQL gateway enforces read-only patterns, max result size, and per-source
  rate limiting; query strings are stored for audit under the snapshot ID.
- Validation diagnostics surface in manifests (`validation_report`) and
  accompanying editorial reports highlighting duplicate labels, conflicting
  mappings, and odd definition lengths.

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

- **License Enforcement**: `LicensingPolicy.requires_masking` determines whether downstream exports must mask specific fields. Automated masking is not yet wired into exporters—flagged under "Gaps".
- **Delta Detection**: ETag comparison marks ingests as `changed` vs `unchanged`, aligning with manifest-based governance.
- **Audit Outputs**: `metadata.json` (per-run manifest) plus `SnapshotInfo.validation_report` populated with SHACL (pyshacl) and Pandera tabular validation summaries.

## Gaps vs. Handbook

| Requirement | Current Status | Notes |
| --- | --- | --- |
| SHACL validation of snapshots | **Available** | `SnapshotInfo.validation_report` contains pyshacl + Pandera summaries.
| Graph traversal/search service | **Missing** | No SPARQL/DuckDB API yet; only static files emitted.
| Vector search indices | **Missing** | Handbook mentions non-authoritative vectors; not yet generated.
| License-aware exports | **Partial** | Policies resolved, but masking/emission enforcement is manual.

## Extending Module 1

- Integrate `pyshacl` validation and populate `validation_report` with pass/fail details.
- Create a DuckDB query service that reads the produced Parquet tables for downstream analytics.
- Add optional embedding generation (with clear non-authoritative flags) to support similarity search.
