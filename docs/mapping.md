# Mapping & Crosswalks Guide (Module 3)

Mapping converts free-text topics or document spans into canonical concept IDs and captures reviewer decisions. While the current implementation is a foundation, it draws a direct path to the Module 3 expectations in `AI-collaboration.md`.

## Pipeline Overview

1. **Candidate Generation** (`mapping/candidate_generation.py`) – Uses simple lexical heuristics (string similarity, alias lookup) to propose potential concept IDs for an input phrase.
2. **Scoring** (`mapping/scoring.py`) – Combines lexical scores with optional policy weights to surface the best candidates.
3. **Decision Layer** (`mapping/decision.py`) – Interfaces designed for human-in-the-loop signoff. Tracks decision rationale and attaches evidence placeholders.
4. **Storage/Repository** (`mapping/repository.py`, `storage.py`) – Abstract persistence layer; currently in-memory with TODOs to connect to a real store.
5. **Pipeline Orchestration** (`mapping/pipeline.py`) – Coordinates the above steps and emits `MappingDecision` records.

## Evidence & Governance

- **Evidence fields** exist in `mapping/models.py` but are optional; future work should make them mandatory and attach citations to satisfy the handbook.
- **Confidence Calibration** is stubbed—`scoring.py` provides deterministic scores but lacks histogram-based calibration.
- **Audit Trail**: `mapping/reporting.py` seeds a reporting structure for precision/recall metrics and ambiguous-case tracking.

## Gaps vs. Handbook

| Requirement | Current Status |
| --- | --- |
| Evidence quotes + rationale | **Partial** – Fields exist but enforcement missing.
| LLM gate for disambiguation | **Missing** – No LLM integration; decisions are purely heuristic.
| Crosswalk maintenance across schemes | **Missing** – `crosswalk.py` outlines structure but no multi-scheme logic yet.
| Throughput targets | **Not measured** – Telemetry hooks exist but no metrics emitted.

## Next Steps

- Enforce evidence capture at the data model level and integrate with Reviewer Workbench (Module 8).
- Plug in vector/embedding similarity for better recall while keeping human approval steps.
- Extend `crosswalk.py` to import existing mappings (LOINC ↔ SNOMED, etc.) and expose diff reports as per governance requirements.

# Module 3 – Mapping & Crosswalks

## Calibration Suite

Builtin calibration support lives in `DomainDetermine.mapping.calibration`. Use `MappingCalibrationSuite` with a list of `CalibrationExample` items to exercise the pipeline against a gold set.

```python
from DomainDetermine.mapping import MappingCalibrationSuite, CalibrationExample

suite = MappingCalibrationSuite(pipeline)
examples = [CalibrationExample("Competition law", "EV:1")]
result = suite.run(examples)
print(result.metrics["accuracy"], result.metrics["resolution_rate"])
```

The suite produces `accuracy`, `resolution_rate`, and reuses the pipeline’s intrinsic metrics. Feed these into governance checks as part of your release gates.

## Guardrails

`DomainDetermine.mapping.policy.MappingPolicyGuardrails` centralizes lexical overlap, edit-distance, and language checks. Configure thresholds with `MappingGuardrailConfig` to mirror the spec’s deterministic fallback requirements and pass a guardrail instance into pipelines or reviewer tools where needed.
