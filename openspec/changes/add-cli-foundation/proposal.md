## Why
Operators need a standard CLI surface aligned to the KOS pipeline so they can drive ingest → plan → audit → publish workflows locally and in CI. We lack a canonical command design that enforces configuration precedence, contexts, and deterministic runs.

## What Changes
- Introduce a CLI command capability spec covering verbs (ingest, snapshot, plan, audit, map, expand, certify, evalgen, publish, diff, rollback, run, report) with idempotent behavior and dry-run switches.
- Define configuration precedence (flags > env > config file) plus named context management for environments/clients.
- Establish progress/logging expectations: structured logs to file, Rich-style TTY summaries, optional JSON logs for CI.

## Impact
- Affected specs: `cli/commands`, `cli/configuration`
- Affected code: CLI entrypoint (Typer/Click), config loader, logging subsystem
