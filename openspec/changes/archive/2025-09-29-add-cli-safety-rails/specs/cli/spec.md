## MODIFIED Requirements
### Requirement: CLI Command Surface
The CLI SHALL expose verbs that mirror system modules (ingest, snapshot, plan, audit, map, expand, certify, evalgen, publish, diff, rollback, run, report) with nouns/options aligned to the relevant artifacts. The CLI SHALL enforce safety rails before mutating artifacts.

#### Scenario: Publish command performs preflight checks
- **WHEN** an operator runs `cli publish --artifact-id plan-v1`
- **THEN** the CLI SHALL execute license flag, forbidden-topic, and integrity preflight checks, failing fast if violations are detected.
- **AND** the CLI SHALL require explicit confirmation (interactive or `--yes`) before continuing.

#### Scenario: Resource guardrails protect remote services
- **WHEN** a mapping command is invoked with a batch larger than the configured limit
- **THEN** the CLI SHALL reject the invocation unless `--max-batch` is raised consciously, and SHALL honor default timeouts plus backoff when rate-limited.

### Requirement: Secrets Handling
The CLI SHALL source secrets from environment variables or a secrets manager, never from plain command-line arguments, and record usage without revealing values.

#### Scenario: Fetch secrets securely
- **WHEN** an operator sets `CLI_SECRET_REF=aws-secrets://prod/registry`
- **THEN** the CLI SHALL resolve credentials via the secrets manager, mask values in logs, and prevent passing secrets as command-line flags.
