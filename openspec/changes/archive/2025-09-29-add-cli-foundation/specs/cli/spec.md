## ADDED Requirements
### Requirement: CLI Command Surface
The CLI SHALL expose verbs that mirror system modules (ingest, snapshot, plan, audit, map, expand, certify, evalgen, publish, diff, rollback, run, report) with nouns/options aligned to the relevant artifacts.

#### Scenario: Run ingest command deterministically
- **WHEN** an operator runs `cli ingest --source sources.json`
- **THEN** the CLI SHALL produce identical artifacts on repeated runs with the same inputs, or no-op if upstream snapshots match (idempotent behavior).
- **AND** the CLI SHALL print a dry-run preview when `--dry-run` is supplied without mutating artifacts.

#### Scenario: Progress and logging emitted
- **WHEN** a long-running command executes
- **THEN** the CLI SHALL show concise TTY progress with status, while writing structured logs (JSON) to disk, and optionally pure JSON output when `--log-format json` is passed.

### Requirement: Configuration & Context Management
The CLI SHALL honor a precedence order (command flags > environment variables > configuration file) and support named contexts (e.g., dev, staging, prod, client-specific).

#### Scenario: Resolve configuration values predictably
- **WHEN** an operator specifies `--artifact-root` on the command line and exports `CLI_ARTIFACT_ROOT`
- **THEN** the CLI SHALL use the command-line value, recording the resolved configuration for traceability.

#### Scenario: Switch contexts seamlessly
- **WHEN** an operator runs `cli context use staging`
- **THEN** the CLI SHALL switch registry endpoints, credentials, and data roots to the `staging` profile, persisting the selection for subsequent commands.
