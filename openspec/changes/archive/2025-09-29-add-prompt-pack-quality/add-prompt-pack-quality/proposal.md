## Why
Calibration assets, automated validation (hallucination, grounding, schema adherence), and quality metrics logging are necessary to keep prompt packs trustworthy but are not yet governed.

## What Changes
- Specify calibration dataset requirements, acceptance yardsticks, automated validators, and quality KPIs.
- Build validation harnesses and metrics pipelines logging grounding fidelity, hallucination rate, cost, and latency metrics.
- Document dashboards, alert thresholds, and governance integration.

## Impact
- Affected specs: `prompt-pack/spec.md`
- Affected code: `src/DomainDetermine/prompt_pack/{calibration,metrics,policies}.py`
- Affected docs: `docs/prompt_pack.md`
- Tests: `tests/test_mapping_calibration.py`, `tests/test_mapping_policy.py`, metrics logging tests
