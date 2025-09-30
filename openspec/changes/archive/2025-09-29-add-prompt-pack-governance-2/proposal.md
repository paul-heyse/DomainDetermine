## Why
Prompt packs require semantic versioning, changelog policies, manifest pinning, and governance events to satisfy reproducibility and audit expectations.

## What Changes
- Extend prompt-pack requirements with semantic version rules, changelog format, and manifest pinning obligations.
- Add tooling for version bumps, hash computation, rationale logging, and governance manifest integration.
- Emit governance events for publish/rollback/waiver actions and update runbooks.

## Impact
- Affected specs: `prompt-pack/spec.md`, `governance/spec.md`
- Affected code: Prompt pack versioning utilities, governance manifest integration
- Affected docs: `docs/prompt_pack.md`, governance runbooks
- Tests: Governance manifest tests, prompt version tooling tests
