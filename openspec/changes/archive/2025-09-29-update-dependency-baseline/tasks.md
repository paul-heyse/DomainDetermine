## 1. Specification / Policy
- [x] 1.1 Document dependency management policy (runtime vs dev extras, installation commands) in tooling docs.

## 2. Implementation
- [x] 2.1 Update `pyproject.toml` and ensure lock/install scripts match the policy.
- [x] 2.2 Adjust CI workflows to install the correct extras bundle.

## 3. Validation
- [x] 3.1 Rebuild environment (`pip install -e .[dev]` or micromamba equivalent).
- [x] 3.2 Run `pytest -q` and `ruff check` as smoke tests.
- [x] 3.3 Execute `openspec validate update-dependency-baseline --strict` (if tied to a tooling spec) or note NA if doc-only.
