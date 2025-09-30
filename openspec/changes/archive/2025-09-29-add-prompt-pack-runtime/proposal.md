## Why
Prompt templates must be enforceable at runtime: model routing, parameter constraints, structured-output enforcement, and retrieval policies need integration with the LLM serving layer. We require a runtime contract so modules use prompts consistently and safely.

## What Changes
- Define prompt pack runtime manifests mapping templates to model routes, parameter ceilings (temperature, max tokens), and fallback order.
- Integrate schema enforcement with guided decoding / structured-output frameworks (e.g., XGrammar, jsonschema validators).
- Implement request builders that apply retrieval policies, token budgeting, and citation enforcement.
- Provide warm-up/testing routines ensuring prompts execute successfully against the serving stack before production use.

## Impact
- Affected specs: prompt-pack, llm-runtime
- Affected code: LLM provider interface, runtime policy enforcement, warm-up scripts
