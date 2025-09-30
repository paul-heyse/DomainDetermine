## 1. Root CLI Refactor
- [x] 1.1 Rework root callback to declare global options with explicit Click/Typer parameters (no implicit secondary flags)
- [x] 1.2 Ensure configuration resolution and logging setup still execute once per invocation

## 2. Operations & Runtime Helpers
- [x] 2.1 Align `operations.py` with the updated option handling (consistent echo/context usage)
- [x] 2.2 Verify dry-run/idempotency logic works after refactor (no duplicate manifest writes)

## 3. Regression Tests
- [x] 3.1 Expand CLI tests to cover `--help`, `--config`, `--dry-run`, context subcommands
- [x] 3.2 Add golden-output assertions for dry-run and ingestion flows

## 4. Documentation
- [x] 4.1 Update README/handbook snippets to reflect corrected CLI usage and flags
- [x] 4.2 Note migration steps for automation scripts if option semantics changed
