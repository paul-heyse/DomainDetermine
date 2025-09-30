## 1. Specification & Approval

- [x] 1.1 Document canonical schema fields, snapshot packaging, validation checks, and observability expectations.
- [x] 1.2 Review with Module 1 stakeholders.

## 2. Implementation

- [x] 2.1 Implement/confirm normalization pipeline across SKOS/OWL/OBO fixtures with provenance capture.
- [x] 2.2 Configure storage outputs (rdflib graph + Parquet/DuckDB tables) with manifests.
- [x] 2.3 Enforce SHACL/tabular checks and license masking policies.
- [x] 2.4 Instrument telemetry (logs, metrics, validation summaries).

## 3. Documentation & Samples

- [x] 3.1 Update `docs/kos_ingestion.md` with governed workflow, manifest schema, and validation guidance.
- [x] 3.2 Provide sample manifests/snapshots (pending fixture refresh).

## 4. Testing & Validation

- [x] 4.1 Add/refresh ingestion pipeline tests and validation harness.
- [x] 4.2 Run `pytest -q` for kos_ingestion modules.
- [x] 4.3 Execute `openspec validate add-kos-ingestion-foundation --strict`.
