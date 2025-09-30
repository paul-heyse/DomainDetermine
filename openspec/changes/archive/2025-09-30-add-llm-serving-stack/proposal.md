## Why
The Triton/TensorRT build and deployment workflow is implemented in scripts but lacks spec coverage, risking drift and unreproducible Module 6 operations.

## What Changes
- Document engine build workflow (quantization, hash pinning), Triton model repository layout, deployment steps, capacity planning, and rollback procedures.
- Update scripts and docs to reflect governed expectations and readiness integration.

## Impact
- Affected specs: `llm-runtime/spec.md`
- Affected code/scripts: `scripts/llm/docker-compose.triton.yml`, `scripts/llm/serve_triton.sh`, `src/DomainDetermine/llm/provider.py`
- Affected docs: `docs/llm_serving_stack.md`
- Tests: LLM provider smoke/integration tests
