## Why
Module 1 must ingest diverse KOS sources, including local files and remote SPARQL endpoints. Without explicit connector requirements, ingest runs risk inconsistent licensing treatment, missing delta detection, and brittle format handling. This change defines the ingestion surface, external connector expectations, and licensing guardrails.

## What Changes
- Specify supported input formats (SKOS Turtle/RDF/XML/JSON-LD, OWL via owlready2, OBO Graph) and the tooling required for each.
- Define connectors for remote sources: SPARQL endpoints with read-only access, authenticated HTTP download with checksum tracking, and retry/backoff policies.
- Capture per-source licensing metadata at ingest and enforce export restrictions via policy switches.
- Establish connector observability: fetch logs, checksum validation, delta detection (ETag/Last-Modified), and error handling contracts.

## Impact
- Affected specs: `kos-ingestion`
- Affected code: ingestion connector layer, fetcher utilities, licensing policy enforcement, logging/metrics for connectors
