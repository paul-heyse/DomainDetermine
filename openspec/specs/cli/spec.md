# cli Specification

## Purpose
Provide a cohesive command-line surface for DomainDetermine operators that manages contexts, orchestrates ingestion/mapping workflows, and supports extensibility through plugins and reusable execution profiles while maintaining strong safety and observability guarantees.
## Requirements
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

### Requirement: CLI Plugin Framework
The CLI SHALL support plugin discovery via entry-point registration for new KOS loaders, mappers, graders, and report renderers, executing plugins in a sandboxed environment with error isolation and trust verification.

#### Scenario: Discover custom loader plugin
- **WHEN** an operator installs a package exposing `cli.plugins.loaders` entry-points
- **THEN** the CLI SHALL list the loader in `cli plugins list`, load it on demand, and continue even if another plugin fails to initialize, logging the error.

#### Scenario: Sandbox plugin execution
- **WHEN** a plugin raises an exception during execution
- **THEN** the CLI SHALL isolate the failure, emit a structured error message, capture stdout/stderr, and prevent the plugin from impacting core command state; unsigned or untrusted plugins SHALL be blocked unless explicitly allowed by policy.

### Requirement: CLI Profiles
The CLI SHALL accept profile manifests that describe sequences of commands with pinned versions, thresholds, and context requirements.

#### Scenario: Execute profile bundle safely
- **WHEN** an operator runs `cli profile run legal-pilot-baseline`
- **THEN** the CLI SHALL validate the manifest, show a dry-run of planned commands, and execute the sequence respecting the profile’s pinned versions and thresholds, aborting if validation errors are detected.
