## ADDED Requirements
### Requirement: LLM Telemetry Schema
LLM requests SHALL emit telemetry records capturing template ID, model name, engine hash, quantisation, schema ID, guided decoding backend, tokens in/out, queue delay (µs), latency (ms), speculative metrics, and error codes. Telemetry SHALL propagate trace IDs to readiness dashboards.

#### Scenario: Telemetry emitted per request
- **WHEN** `generate_json`, `rank_candidates`, or `judge` endpoints are invoked
- **THEN** the provider SHALL log structured telemetry with the required fields and send metrics to the observability pipeline.

### Requirement: Cost & Token Accounting
LLM operations SHALL compute token costs per request (prompt + completion) using configured pricing tables, persist totals per template/version, and expose cost dashboards for finance reporting.

#### Scenario: Cost tracking
- **WHEN** a request completes
- **THEN** the provider SHALL calculate token costs, store them in the metrics repository, and update alert thresholds if cost exceeds configured limits.

### Requirement: Error & Alerting Policies
LLM observability SHALL define alert thresholds for queue delay, token throughput, error rate, and cost spikes. Alerts SHALL integrate with readiness incident workflows and governance events.

#### Scenario: Queue delay alert
- **WHEN** average queue delay exceeds 250 ms for 5 minutes
- **THEN** an alert SHALL be triggered, governance event emitted, and readiness dashboard flagged with `LLM_AT_RISK` status.

### Requirement: Debug Logs & Sanitization
When debug logging is enabled, the provider SHALL capture sanitized input/output snippets (respecting privacy and license policies), tagged with trace IDs, and store them in short-lived secure storage for troubleshooting.

#### Scenario: Sanitized debug log
- **WHEN** debug logging is turned on for a request
- **THEN** the provider SHALL redact PII/licensed content and store sanitized logs with retention policy (<24h) for incident responders.
