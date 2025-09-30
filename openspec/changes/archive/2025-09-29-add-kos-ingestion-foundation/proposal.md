## Why
Module 1 needs a canonical way to ingest and normalize heterogeneous knowledge organization systems (KOS) before any downstream planning or mapping can happen. Today there is no shared schema, snapshot process, or guarantee that concepts have stable identifiers and provenance. We must establish a foundation that makes each KOS snapshot reproducible and queryable.

## What Changes
- Define the initial `kos-ingestion` capability spec that covers the canonical concept model, snapshot manifests, and storage expectations.
- Introduce a normalization pipeline that unifies SKOS, OWL, and OBO concepts into consistent identifiers, labels, definitions, hierarchy edges, mappings, and provenance.
- Establish snapshot packaging: rdflib-backed graph store plus columnar Parquet/DuckDB tables with manifests and hashes; include policy flags for license-restricted exports.
- Add observability requirements for ingest runs (structured logs, metrics) and lifecycle hooks to pin downstream artifacts to a snapshot ID.

## Impact
- Affected specs: `kos-ingestion`
- Affected code: ingestion CLI/jobs, normalization utilities, storage layout, manifest generation, logging/metrics plumbing
