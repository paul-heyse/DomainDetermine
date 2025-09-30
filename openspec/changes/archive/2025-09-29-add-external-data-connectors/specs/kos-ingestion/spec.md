## ADDED Requirements

### Requirement: External Connector Coverage

The system SHALL provide vetted connectors for all external KOS data sources described in `AI-collaboration.md`, covering file-based inputs, remote endpoints, licensed feeds, and operational governance.

#### Scenario: SKOS/OWL/OBO file ingestion

- **WHEN** an ingest job is configured with a local or remote SKOS Turtle/RDF/XML/JSON-LD file, OWL ontology, or OBO Graph artifact
- **THEN** the connector SHALL fetch (if remote) with TLS verification, checksum validation (SHA-256), size guardrails, and resumable downloads; parse using the designated parser (`rdflib`, `owlready2`, `pronto`/`obonet`), log parse statistics, capture provenance (source URI, retrieval timestamp, content hash, license tag), and emit structured errors for malformed inputs with reproducible repro steps.

#### Scenario: Authenticated HTTP ingestion

- **WHEN** a source requires authenticated HTTP access (API tokens, basic auth, signed URLs)
- **THEN** the connector SHALL support credential injection via environment or secrets manager, rotate tokens before expiry, respect per-source throttle policies, implement retry/backoff with jitter, detect deltas using ETag and Last-Modified headers, and record authentication events (success/failure) without exposing secrets in logs.

#### Scenario: SPARQL endpoint ingestion

- **WHEN** an ingest job targets a read-only SPARQL endpoint
- **THEN** the connector SHALL constrain queries to a whitelisted library, paginate large result sets, enforce timeout and rate limits, cache query responses keyed by (endpoint, query, snapshot), sanitize input to prevent injection, and record endpoint metadata (service description, version, auth mode) in the snapshot manifest.

#### Scenario: Licensed source enforcement

- **WHEN** a connector fetches a KOS with licensing restrictions (e.g., SNOMED CT)
- **THEN** it SHALL capture license metadata, enforce policy toggles to block export of restricted data, produce redacted artifacts where required, emit compliance logs, and fail the ingest with actionable errors if licensing terms are violated or credentials are missing.

#### Scenario: Connector telemetry & health

- **WHEN** connectors run in production or CI
- **THEN** they SHALL emit OpenTelemetry spans and structured logs with fetch duration, bytes transferred, retry counts, cache hits, error taxonomies, and licensing enforcement events; expose Prometheus-compatible metrics for latency, throughput, and failure rate; and support health probes that validate endpoint reachability ahead of scheduled runs.

#### Scenario: Validation harness and fixtures

- **WHEN** developing or upgrading connectors
- **THEN** the system SHALL provide golden fixtures (sample SKOS, OWL, OBO files; mocked SPARQL responses), contract tests verifying parser correctness, schema validation (pyshacl, pandera), and integration tests that simulate failures (network outages, auth errors, corrupted files) to ensure graceful degradation and targeted remediation guidance.

#### Scenario: Governance & documentation

- **WHEN** onboarding a new connector or updating an existing one
- **THEN** the manifest SHALL record connector configuration (version, params, credential references), content hash, policy flags, and runbook links; documentation SHALL include onboarding checklists, incident response steps, delta detection strategy, and support contacts to comply with governance requirements in Module 7.
