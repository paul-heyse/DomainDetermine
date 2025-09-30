## 1. Specification & Approval
- [x] 1.1 Draft CLI spec updates for PluginTrustPolicy, sandbox behaviour, and profile validation, then request review.
- [x] 1.2 Align proposal with Module 7 governance guidance on trusted extensions.

## 2. Implementation
- [x] 2.1 Extend `PluginTrustPolicy` (config + env overrides) and enforce signature allowlists in `cli/plugins.py`.
- [x] 2.2 Wrap plugin execution with sandbox capture (stdout/stderr, env guards) and expose trust status in `cli plugins list`.
- [x] 2.3 Validate profile manifests against command signatures and improve dry-run preview messaging.
- [x] 2.4 Update CLI docs (`docs/cli.md`, `docs/cli_extensibility.md`) with signature workflow and sandbox guidance.

## 3. Testing & Validation
- [x] 3.1 Add regression tests in `tests/test_cli_plugins.py` and `tests/test_cli_profiles.py`.
- [x] 3.2 Execute `pytest -q tests/test_cli_plugins.py tests/test_cli_profiles.py`.
- [x] 3.3 Run `openspec validate update-cli-extensibility-security --strict`.
