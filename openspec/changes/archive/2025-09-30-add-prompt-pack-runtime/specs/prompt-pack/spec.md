## ADDED Requirements
### Requirement: Runtime Manifest Format
Prompt packs SHALL distribute a runtime manifest (`runtime_manifest.json`) mapping templates to runtime routes, parameter ceilings (temperature, max tokens, top_p), fallback order, and retrieval policy references. Manifests SHALL include checksum metadata and SHALL be validated before deployment.

#### Scenario: Manifest validation failure
- **WHEN** the manifest omits required fields (e.g., fallback route, tokenizer info)
- **THEN** the runtime validator SHALL fail and block deployment until the manifest is corrected.

### Requirement: Guided Decoding Enforcement
Templates requiring structured output SHALL specify a guided decoding configuration (e.g., xgrammar JSON schema or regex grammar). The runtime SHALL enforce guided decoding, refusing to execute templates lacking the required schema or tokenizer info cache.

#### Scenario: Missing guided decoding config
- **WHEN** a template declared as `requires_guided_output: true` is invoked without a schema reference
- **THEN** the runtime SHALL raise an error and prevent execution.

### Requirement: Retrieval & Token Budget Controls
Runtime executions SHALL honor retrieval policies and token budgets defined in the prompt pack. Requests exceeding budgets SHALL be truncated or rejected, and retrieval sources outside the allowlist SHALL be blocked.

#### Scenario: Token budget exceeded
- **WHEN** a request attempts to allocate more prompt tokens than the manifest budget
- **THEN** the runtime SHALL reject the request with a `TOKEN_BUDGET_EXCEEDED` error, logging the event for governance review.

### Requirement: Observability & Telemetry
Runtime executions SHALL emit structured telemetry including template ID/version, route, guided decoding backend, tokens in/out, queue delay, latency, cost, and fallback usage. Telemetry SHALL integrate with LLM observability dashboards and readiness metrics.

#### Scenario: Telemetry emitted per execution
- **WHEN** a template is executed
- **THEN** telemetry SHALL capture runtime metadata and send it to the observability pipeline with trace IDs, enabling readiness dashboards to display per-template statistics.
