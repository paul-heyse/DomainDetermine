## ADDED Requirements
### Requirement: Runtime Manifest Integration
The prompt pack SHALL provide runtime manifests that map each template to its model route, parameter ceilings (temperature, max output tokens), and fallback order, ensuring the LLM provider reads these manifests when issuing requests.

#### Scenario: Missing runtime manifest entry
- **WHEN** a template is invoked without a corresponding runtime manifest entry
- **THEN** the provider SHALL fail the request and log a configuration error referencing the missing manifest

### Requirement: Structured Output Enforcement
LLM requests SHALL enforce schema-constrained outputs via guided decoding or structured-output validation, rejecting responses that fail schema checks before downstream modules consume them.

#### Scenario: Output validation failure
- **WHEN** a response violates the schema (missing fields, invalid enumerations)
- **THEN** the provider SHALL trigger re-generation or error handling logic, preventing invalid data from propagating

### Requirement: Retrieval & Citation Policy Enforcement
At runtime, templates SHALL enforce retrieval policies (allowed sources, token budgets) and citation requirements, ensuring evidence spans are tracked and referenced in outputs.

#### Scenario: Evidence budget exceeded
- **WHEN** a request exceeds the configured token budget for an evidence source
- **THEN** the provider SHALL trim or reject the request, logging the policy violation

### Requirement: Warm-Up & Health Checks
The system SHALL run warm-up sequences for every template to preload caches and verify schema-compliant outputs; health checks must surface failures to the observability stack before enabling production traffic.

#### Scenario: Warm-up failure
- **WHEN** a template fails warm-up validation
- **THEN** the system SHALL mark the endpoint unhealthy, block production traffic for that template, and emit an alert for remediation
