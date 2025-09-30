## Why
The current Typer-based CLI fails to start (`Secondary flag is not valid for non-boolean flag`) and exits before any command executes. Global options (e.g., `--config`, `--dry-run`, `--context`) are not parsed reliably, preventing ingestion and context commands from running and breaking automation that depends on the CLI. We need to harden the CLI option handling, align with the latest Typer/Click expectations, and restore deterministic behaviour with regression tests.

## What Changes
- Audit and redesign the root CLI callback so global options are correctly declared (particularly boolean flags like `--dry-run` and value-bearing options like `--config`).
- Refactor supporting helpers (`operations.py`, logging hooks) to use Click primitives consistently, removing mixed Typer/Click APIs that cause runtime errors.
- Add regression tests for CLI help, global options, dry-run behaviour, context commands, and ingestion idempotency.
- Update developer documentation/runbooks describing CLI usage and option semantics.

## Impact
- Affected specs: cli
- Affected code: `src/DomainDetermine/cli/app.py`, `src/DomainDetermine/cli/operations.py`, CLI tests, documentation
