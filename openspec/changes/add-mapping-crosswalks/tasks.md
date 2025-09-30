## 1. Specification & Approval
- [x] 1.1 Capture mapping mission, pipeline stages, crosswalk workflow, quality metrics, and HITL processes in the spec.
- [ ] 1.2 Review with Module 3 stakeholders.

## 2. Implementation
- [ ] 2.1 Ensure normalization, candidate generation, scoring, LLM adjudication, and fallback stages meet spec requirements.
- [ ] 2.2 Persist mapping/crosswalk artifacts with provenance and governance metadata.
- [ ] 2.3 Instrument telemetry (precision@1, recall@k, deferral rate, latency, cost) and integrate with observability.
- [ ] 2.4 Build reviewer tooling/queues with structured reason codes.

## 3. Calibration & Documentation
- [ ] 3.1 Produce calibration datasets/tests and update `docs/mapping.md` with workflows.
- [ ] 3.2 Document governance linkage (manifest references, audit reports).

## 4. Testing & Validation
- [ ] 4.1 Expand mapping pipeline and calibration tests.
- [ ] 4.2 Run `pytest -q tests/test_mapping_pipeline.py tests/test_mapping_calibration.py`.
- [x] 4.3 Execute `openspec validate add-mapping-crosswalks --strict`.
