## Why

Once the ingestion foundation and connectors exist, Module 1 must expose reliable traversal/search APIs and enforce data quality gates. Without clearly defined query semantics and validation requirements, downstream modules cannot depend on constant-time subtrees, accurate path-to-root calculations, or trustworthy mapping resolution.

## What Changes

- Specify query and traversal operations (get by ID, children, parents, siblings, subtree, leaves, path-to-root, label search, mapping resolution) and their performance expectations.
- Define caching and indexing strategies, including text search (rapidfuzz) and optional semantic embeddings, with policies that mark embeddings as non-authoritative.
- Establish data quality validation: SHACL shapes for core structural checks, Pandera dataframe schemas for tabular integrity, and editorial diagnostics for duplicates, conflicting mappings, and capitalization issues.
- Describe telemetry for query services (latency, cache hit rate) and SPARQL gateway safeguards (timeouts, result limits, whitelisting).

## Impact

- Affected specs: `kos-ingestion`
- Affected code: query service layer, caching/indexing infrastructure, validation suites, telemetry instrumentation
