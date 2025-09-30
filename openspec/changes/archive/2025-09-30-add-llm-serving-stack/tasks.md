## 1. Specification & Approval

- [x] 1.1 Describe engine build, deployment, configuration, and rollback requirements in the spec.
- [x] 1.2 Review with Module 6 stakeholders.

## 2. Implementation

- [x] 2.1 Update scripts/docs to capture build steps (quantization, tokenizer info, hash pinning) and deployment layout.
- [x] 2.2 Ensure provider configuration enforces engine hash/quantisation headers and integrates with readiness telemetry.
- [x] 2.3 Document capacity planning and rollback procedures.

## 3. Testing & Validation

- [x] 3.1 Run LLM provider smoke/integration tests.
- [x] 3.2 Execute `openspec validate add-llm-serving-stack --strict`.
