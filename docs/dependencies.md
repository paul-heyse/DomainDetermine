# Dependency Management Policy

This repository separates runtime dependencies from development tooling so that CI, local development, and production deployments remain predictable.

## Runtime dependencies

`pyproject.toml` lists the packages required to run the DomainDetermine modules (ingestion, coverage planning, mapping, overlay, service APIs, LLM integrations). Install them with:

```bash
pip install -e .
```

or, when using micromamba (preferred for CI/local dev), after creating the environment:

```bash
micromamba run -n dd pip install -e .
```

## Optional extras

| Extra | Purpose | Command |
|-------|---------|---------|
| `dev` | Linters, formatters, test frameworks (`ruff`, `black`, `pytest`, `mypy`, `pre-commit`) | `pip install -e .[dev]` |
| `service` | Observability add-ons for the FastAPI service (OpenTelemetry exporters) | `pip install -e .[service]` |
| `docs` | MkDocs tooling for publishing documentation | `pip install -e .[docs]` |

Combine extras as needed, e.g. `pip install -e .[dev,service]`.

## Environment bootstrap

The recommended flow for new contributors:

```bash
micromamba create -n dd python=3.12
micromamba activate dd
pip install -e .[dev,service]
```

Run the smoke tests after installation:

```bash
pytest -q
ruff check src tests
```

## CI alignment

The GitHub Actions workflow (`.github/workflows/ci.yml`) mirrors this policy by installing the project with `pip install -e .[dev,service]` after the micromamba environment is created. This keeps the CI dependencies in sync with local expectations.

## Updating dependencies

1. Modify `pyproject.toml` (and `environment.yml` if the micromamba env needs adjustments).
2. Rebuild your environment (`pip install -e .[dev,service]`).
3. Run `pytest -q` and `ruff check src tests`.
4. Update this document if the policy or extras change.
