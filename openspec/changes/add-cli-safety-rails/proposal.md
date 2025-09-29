## Why
Running publish and rollback workflows today lacks enforced preflight guards, destructive confirmations, or resource controls. We need safety rails baked into the CLI to prevent accidental data changes, respect licensing, and avoid overloading remote systems.

## What Changes
- Add CLI spec deltas covering preflight checks (license flags, forbidden topics, integrity), confirmation prompts for destructive commands, and resource guardrails (batch limits, default timeouts, rate-limit awareness).
- Introduce secrets handling rules ensuring no secrets on CLI flags and routed through environment/secret managers.

## Impact
- Affected specs: `cli/commands`, `security/secrets`
- Affected code: CLI middleware, preflight pipeline, confirmation prompts, secret resolver
