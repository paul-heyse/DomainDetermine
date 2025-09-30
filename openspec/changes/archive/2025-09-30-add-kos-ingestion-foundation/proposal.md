## Why
The KOS ingestion pipeline (canonical schema, normalization, validation, telemetry) powers Module 1 but lacks a governing spec ensuring consistent snapshots and provenance.

## What Changes
- Define the canonical concept schema, snapshot packaging (graph + columnar tables), validation (SHACL + tabular), observability, and licensing enforcement requirements.
- Document supported source formats/tooling and ensure manifests capture provenance.
- Update docs and tests to reflect governed expectations.

## Impact
- Affected specs: `kos-ingestion/spec.md`
- Affected code: `src/DomainDetermine/kos_ingestion/{models,pipeline,validation,query}.py`
- Affected docs: `docs/kos_ingestion.md`
- Tests: Ingestion pipeline + validation tests
