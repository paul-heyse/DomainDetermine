# DomainDetermine Architecture Overview

This document maps the current implementation to the blueprint in `AI-collaboration.md`. Each module summary includes:

- **Purpose** – Why the module exists in the overall workflow.
- **Primary Components** – Key packages/classes in this repo.
- **Outputs** – Artefacts emitted today.
- **Gaps vs. Handbook** – Notable differences from the reference design that should be addressed in future iterations.

## Module 1 — KOS Ingestion & Graph Service

- **Purpose**: Ingest SKOS/OWL/OBO sources, normalise them into canonical concept frames, and persist graph + tabular snapshots for downstream use.
- **Primary Components**:
  - `kos_ingestion/fetchers.py`: HTTP/SPARQL fetchers with license-aware metadata capture.
  - `kos_ingestion/parsers.py` & `normalization.py`: Parser factory and normalisation pipeline assembling graph/table outputs.
  - `kos_ingestion/pipeline.py`: `IngestConnector` orchestrates fetch → parse → snapshot → metadata.
  - `kos_ingestion/models.py`: Source, policy, and snapshot dataclasses.
- **Outputs**: `SnapshotInfo` (manifest + Parquet tables), connector metrics, policy-aware metadata.
- **Gaps vs. Handbook**:
  - No SHACL validation or graph query service yet (`pyshacl`, SPARQL endpoints pending).
  - Vector index hooks are not implemented; metadata carries placeholders.
  - License masking is recorded but not enforced automatically on exports.

## Module 2 — Coverage Planner & Sampler

- **Purpose**: Turn a concept frame subset plus business constraints into a reproducible coverage plan with quotas, policy annotations, and diagnostics.
- **Primary Components**:
  - `coverage_planner/planner.py`: `CoveragePlanner` orchestrates filtration, stratification, allocation, and diagnostics.
  - `coverage_planner/allocation.py`: Deterministic strategies (uniform/proportional/Neyman/cost-constrained) with fairness controls.
  - `coverage_planner/combinatorics.py`: Pairwise facet reduction to avoid combinatorial explosion.
  - `coverage_planner/diagnostics.py`: Coverage health metrics (branch/depth/facet distributions, entropy, Gini, red flags).
  - `coverage_planner/models.py`: Rich data model for concepts, facets, constraints, plan rows, metadata, and governance fields.
- **Outputs**: `CoveragePlan` aggregate with quota table, allocation metadata/report, diagnostics, quarantine ledger, solver failure manifests, and LLM suggestion ledger.
- **Gaps vs. Handbook**:
  - What-if panel is represented as metadata fields; interactive UI not shipped.
  - LLM-assisted refinements limited to difficulty overrides; no subtopic proposal flow yet.
  - LP solver-backed cost-constrained strategy with fallback manifest is now available.
  - Governance registry integration (signing, diff storage) remains TODO.

## Module 3 — Mapping & Crosswalks

- **Purpose**: Align free text (prompts, spans, documents) with canonical concept IDs and maintain cross-scheme mappings.
- **Primary Components**:
  - `mapping/candidate_generation.py`, `scoring.py`: Primitive heuristics for candidate set construction (string similarity, synonyms).
  - `mapping/decision.py`: HITL adjudication helpers, scoring aggregation.
  - `mapping/pipeline.py`: Stub pipeline for mapping execution.
  - `mapping/models.py`: Mapping request/decision dataclasses.
- **Outputs**: Currently limited to in-memory candidate lists and decision logs; persistent storage is a TODO.
- **Gaps vs. Handbook**:
  - Evidence capture (citations, explanations) is not enforced.
  - Confidence calibration, judge prompts, and retraining loops are placeholders.
  - Crosswalk maintenance across external schemes is not implemented.

## Module 4 — Overlay Curation

- **Purpose**: Govern curated extension topics layered on top of the base KOS when coverage gaps appear.
- **Primary Components**:
  - `overlay/` package scaffolds models and pipeline for overlay proposals (currently skeletal).
- **Outputs**: Stubs only.
- **Gaps vs. Handbook**:
  - Full reviewer workflow, duplicate detection, and RAG-grounded evidence missing.
  - No published overlay manifest or namespace management yet.

## Cross-Cutting Services (Future Work)

The handbook lists additional modules (auditing/certification, eval suite generation, governance registry, reviewer workbench, telemetry). The current repository does not yet include:

- Automated auditing certificates or fairness score calculators beyond high-level diagnostics.
- Eval suite scaffolding (slice definitions, judge prompts, threshold governance).
- Governance registry (semantic version store, manifest signing, waiver ledger).
- Telemetry pipelines for cost observability and run bundles.

These omissions are flagged to keep the implementation aligned with the long-term blueprint.
