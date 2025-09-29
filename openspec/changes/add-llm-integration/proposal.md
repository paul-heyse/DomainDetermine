## Why
Modules 3–6 need a unified interface for the new Triton-served Qwen3 engine. We must integrate guided JSON workflows, schema management, and runtime policies without duplicating LLM-specific logic across components.

## What Changes
- Implement an LLM provider abstraction that routes requests (`generate_json`, `rank_candidates`, `judge`) to the Triton endpoint with appropriate guidance and logging.
- Update mapping, overlay, evaluation, and judge workflows to use the provider while keeping deterministic parameters.
- Add schema registry support for guided decoding (JSON schema/EBNF) and utilities to generate tokenizer info required by xgrammar.
- Provide warm-up routines and integration tests to ensure modules interact correctly with the local Triton instance.

## Impact
- Affected specs: llm-runtime
- Affected code: mapping pipeline, overlay proposal generator, evaluation judge infrastructure, shared LLM client utilities
