## Why
Multi-pass mapping, crosswalk storage, telemetry, and human-in-the-loop operations are implemented but not governed, leaving Module 3 without enforceable requirements.

## What Changes
- Define mapping requirements covering mission/success criteria, inputs/outputs, trust boundary, pipeline stages, crosswalk workflow, storage/indexing, quality controls, HITL operations, and governance compliance.
- Implement/confirm pipeline components, telemetry, crosswalk storage, and reviewer tooling aligned with the spec.
- Document calibration/testing and governance integration.

## Impact
- Affected specs: `mapping/spec.md`
- Affected code: `src/DomainDetermine/mapping/{candidate_generation,decision,pipeline,storage,telemetry}.py`
- Affected docs: `docs/mapping.md`
- Tests: `tests/test_mapping_pipeline.py`, calibration/telemetry tests
