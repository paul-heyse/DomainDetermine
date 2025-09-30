## ADDED Requirements

### Requirement: LLM Provider Interface

The system SHALL expose a centralized LLM provider with methods `generate_json`, `rank_candidates`, and `judge`, each enforcing approved decoding parameters and logging engine metadata for reproducibility.

#### Scenario: Provider logs request metadata

- **WHEN** any module calls the LLM provider
- **THEN** the provider SHALL send the request to Triton with the correct guided decoding settings and log engine hash, quantization method, schema identifier, tokens in/out, and latency

### Requirement: Guided Schema Registry

The governance layer SHALL maintain versioned JSON schemas/EBNF grammars used for guided decoding, exposing `load_record` semantics that validate schema presence and provide descriptive metadata.

#### Scenario: Schema version mismatch

- **WHEN** a module requests guided decoding with a schema version that is not registered via `load_record`
- **THEN** the registry SHALL raise an error describing the missing schema, preventing the provider from issuing the request

### Requirement: Tokenizer Info Cache

The system SHALL generate and cache tokenizer metadata files compatible with Triton xgrammar guided decoding so that repeated requests reuse the same tokenizer info artifacts.

#### Scenario: Tokenizer cache miss

- **WHEN** a guided decoding request is made for a tokenizer that lacks a cached info file
- **THEN** the integration SHALL produce a deterministic tokenizer info JSON, store it in the cache, and reuse it for subsequent requests

### Requirement: Warm-Up & Health Procedures

The integration SHALL include warm-up routines to seed the KV cache and verify schema-bound responses before routing live traffic, ensuring first-byte latency meets SLO thresholds.

#### Scenario: Warm-up failing

- **WHEN** warm-up sequences do not return valid schema-conforming JSON
- **THEN** the system SHALL mark the LLM endpoint unhealthy and prevent production traffic until remediation occurs
