## ADDED Requirements
### Requirement: LLM Observability Metrics
The system SHALL collect and store per-request metrics (latency, queue delay, tokens in/out, KV reuse ratio, speculation acceptance ratio) from the Triton TRT-LLM backend and expose dashboards with SLO thresholds.

#### Scenario: Latency SLO breach
- **WHEN** rolling latency exceeds the configured SLO
- **THEN** alerts SHALL trigger and incident playbooks SHALL be followed to mitigate the issue

### Requirement: Governance Event Integration
LLM lifecycle events (engine published, warm-up completed, rollback) SHALL be recorded in the governance event log with corresponding manifests and backup entries.

#### Scenario: Warm-up failure event
- **WHEN** a warm-up sequence fails
- **THEN** the governance log SHALL receive an event marking the endpoint unhealthy and referencing the engine hash

### Requirement: Backup & Recovery for LLM Artifacts
Engine binaries, tokenizer info, guided schema registries, and config files SHALL be included in the governance backup plan with documented restore procedures.

#### Scenario: Restore from backup
- **WHEN** a restore is executed
- **THEN** the process SHALL fetch the recorded engine hash, tokenizer files, schema registry, and Triton config to rebuild the serving stack within RTO
