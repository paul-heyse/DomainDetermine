## Why
Plugin signatures, sandbox isolation, and profile validation were added to the CLI but the canonical spec still lacks requirements covering trust policy, sandboxing, and dry-run previews. Without a governed change, Module 7 security controls cannot rely on the CLI surface.

## What Changes
- Update CLI requirements to describe PluginTrustPolicy configuration, signature enforcement, sandboxed execution, and profile manifest validation/dry-run behaviour.
- Improve `cli plugins list` to surface trust status, block untrusted plugins unless explicitly allowed, and capture plugin stdout/stderr for diagnostics.
- Document plugin authoring and profile usage, and add regression tests for signature policies and manifest validation.

## Impact
- Affected specs: `cli/spec.md`
- Affected code: `src/DomainDetermine/cli/{config,plugins,app,profiles,operations}.py`
- Affected docs: `docs/cli.md`, `docs/cli_extensibility.md`
- Tests: `tests/test_cli_plugins.py`, `tests/test_cli_profiles.py`
