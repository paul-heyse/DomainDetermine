## Why

Module 1 currently defines high-level ingestion behaviors, but we lack a concrete, end-to-end specification for every external connector described in `AI-collaboration.md`. Without explicit requirements for file parsers, remote fetchers, authenticated endpoints, licensing enforcement, observability, and validation harnesses, the ingest surface risks drift, inconsistent provenance capture, and brittle integrations when onboarding new knowledge organization systems (KOS). A detailed proposal is needed to codify connector responsibilities, harden retries and delta detection, formalize licensing gates, and define comprehensive test coverage.

## What Changes

- Enumerate all supported connector families (SKOS/OWL/OBO file loaders, HTTP/HTTPS fetchers with checksum validation, SPARQL endpoints, authenticated licensed sources) and define mandatory behaviors for fetch, parsing, provenance capture, and error handling.
- Specify configuration surfaces for credentials, throttling, caching, and delta detection (ETag/Last-Modified, checksum comparison) to ensure reproducible ingest snapshots.
- Introduce detailed telemetry, logging, and metrics requirements per connector (latency, retries, cache hits, licensing enforcement events) aligned with observability conventions in `AI-collaboration.md`.
- Define validation harnesses and golden fixtures for each connector type, including contract tests for rdflib/owlready2/pronto parsing, SPARQLWrapper query sandboxing, and licensing policy enforcement scenarios.
- Extend governance coverage by requiring manifests to store connector configuration hashes, policy flags, and source-specific runbooks for onboarding and incident response.

## Impact

- Affected specs: `kos-ingestion`
- Affected code: ingestion connector layer, HTTP/SPARQL fetch utilities, credential management, observability pipeline, validation harnesses, test fixtures
