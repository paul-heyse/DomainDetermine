## 1. LLM Provider Abstraction
- [x] 1.1 Implement Python client wrapping Triton endpoint with methods `generate_json`, `rank_candidates`, `judge`
- [x] 1.2 Log request metadata (engine hash, quantization, schema id, tokens) for observability

## 2. Module Integration
- [x] 2.1 Update mapping module to use `generate_json` with guided schema outputs
- [x] 2.2 Update overlay expansion to use provider for proposal scoring and judge workflows for evaluation

## 3. Schema & Guidance Utilities
- [x] 3.1 Add schema registry for JSON/EBNF grammars with versioning and documentation
- [x] 3.2 Provide tokenizer info generation and caching for xgrammar guided decoding

## 4. Testing & Warm-up
- [x] 4.1 Implement warm-up routines to seed KV cache and ensure first-request latency meets SLOs
- [x] 4.2 Add integration tests/mocks covering provider usage across modules
