## Why
Runtime manifests, guided decoding enforcement, retrieval/token budgeting, and fallback choreography must be governed so Module 6 LLM operations remain deterministic and auditable.

## What Changes
- Define runtime manifest format, fallback order, and parameter ceilings for prompt templates.
- Enforce guided decoding/generation policies and retrieval/token budget controls tied to prompt pack policies.
- Document operational runbooks, observability, and policy enforcement for runtime execution.

## Impact
- Affected specs: `prompt-pack/spec.md`, `llm-runtime/spec.md`
- Affected code: `src/DomainDetermine/prompt_pack/runtime.py`, `src/DomainDetermine/llm/{provider,tokenizer}.py`
- Affected docs: `docs/prompt_pack.md`, `docs/llm_serving_stack.md`, `docs/llm_observability.md`
- Tests: runtime manifest/LLM provider tests
