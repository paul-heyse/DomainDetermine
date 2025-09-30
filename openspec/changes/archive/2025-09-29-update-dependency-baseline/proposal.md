## Why
The dependency baseline changed (deduplicating `SPARQLWrapper`, adding `transformers`, introducing `[project.optional-dependencies].dev`). Without a governed update, environment reproducibility and CI guidance remain unclear.

## What Changes
- Document runtime vs development dependency policy (micromamba vs pip, extras usage) and justify library additions/removals.
- Update `pyproject.toml` and CI/environment scripts to align with the policy and communicate upgrade steps.
- Validate environment rebuild (`pip install -e .[dev]` or micromamba equivalent) and test suite execution.

## Impact
- Affected docs: Environment/tooling guides, README, deployment docs
- Affected config: `pyproject.toml`, CI environment setup
- Tests: `pytest -q`, linting
