## ADDED Requirements
### Requirement: CLI Global Option Compatibility
The CLI SHALL parse global options (`--config`, `--context`, `--dry-run`, `--verbose`, `--log-format`) without raising Typer/Click errors, ensuring they can be combined with any command.

#### Scenario: CLI invoked with dry-run
- **WHEN** the command `dd --config cfg.toml --dry-run ingest sources.json` is executed
- **THEN** the CLI SHALL exit with code 0 and print the dry-run preview instead of raising option parsing errors

### Requirement: CLI Context Commands
The CLI SHALL expose a `context` command group supporting `list`, `use`, and `show` operations that function under the new option handling.

#### Scenario: Context show
- **WHEN** the command `dd --config cfg.toml context show` runs
- **THEN** the CLI SHALL output the target context configuration as JSON without errors

### Requirement: CLI Ingestion Idempotency
The CLI ingestion command SHALL remain idempotent, skipping repeated runs with unchanged fingerprints while logging `[no-op]` and `[dry-run]` statuses as appropriate.

#### Scenario: Repeated ingestion
- **WHEN** `dd ingest sources.json` is run twice with unchanged inputs
- **THEN** the second invocation SHALL report a `[no-op]` status instead of re-executing the operation
