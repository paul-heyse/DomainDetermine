# CLI Extensibility Guide

This guide explains how to extend the DomainDetermine CLI with custom plugins and profile manifests. Read it alongside `docs/cli.md` and the OpenSpec requirements under `openspec/specs/cli/spec.md`.

## Plugin Architecture

The CLI exposes four plugin categories via Python entry points:

| Category | Entry point group              | Purpose |
|----------|--------------------------------|---------|
| loaders  | `cli.plugins.loaders`          | Extend KOS ingestion and source prep pipelines. |
| mappers  | `cli.plugins.mappers`          | Contribute candidate generation or decision helpers. |
| graders  | `cli.plugins.graders`          | Provide custom grading/evaluation logic. |
| renderers| `cli.plugins.report_renderers` | Add new report exporters or dashboards. |

### Authoring a Plugin

1. Define a callable that accepts `runtime` (a `CommandRuntime`) and keyword arguments:
   ```python
   def legal_ingest_loader(*, runtime, source: str) -> None:
       """Import legal source data into a staging directory."""
       runtime.logger.info("Loading source", extra={"source": source})
   ```
2. Register the callable in your `pyproject.toml` (or `setup.cfg`) entry points:
   ```toml
   [project.entry-points."cli.plugins.loaders"]
   legal_ingest = "my_package.plugins:legal_ingest_loader"
   ```
3. Compute the plugin signature and share it with operators:
   ```bash
   python - <<'PY'
   import hashlib, inspect
   from my_package import plugins

   path = inspect.getfile(plugins.legal_ingest_loader)
   digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
   print("legal_ingest=sha256:" + digest)
   PY
   ```
4. Operators add the signature to `cli.toml` (or `DD_TRUSTED_PLUGIN_SIGNATURES`).

### Sandbox & Safety

* Plugins run inside a sandbox that captures stdout/stderr and provides an isolated scratch directory via `DD_PLUGIN_SANDBOX_DIR`.
* Signature verification is enforced unless `allow_unsigned = true` or `DD_ALLOW_UNSIGNED_PLUGINS=1`.
* The CLI logs failed loads (`plugins list`) and blocks execution when a signature is missing or mismatched.

## Profile Manifests

Profiles describe repeatable command bundles. Manifests support TOML or JSON encodings with the fields:

| Field        | Required | Description |
|--------------|----------|-------------|
| `name`       | ✅        | Operator-friendly identifier. |
| `cli_version`| ✅        | CLI version the profile was authored against. |
| `description`|          | Optional summary shown in previews. |
| `steps`      | ✅        | Ordered list of command steps. |

Each step requires a `verb` matching a CLI command and supplies keyword arguments that align with that command's Typer signature. During `profile run` the CLI:

1. Validates the verb exists and required arguments are present.
2. Reports unexpected arguments before invoking any command.
3. Prints a dry-run preview of each step.
4. Executes the steps sequentially unless `--dry-run` is active.

Example manifest:

```toml
name = "legal-baseline"
cli_version = "0.1.0"
description = "End-to-end workflow for the legal pilot"

[[steps]]
verb = "ingest"
source = "configs/legal_sources.json"

[[steps]]
verb = "plan"
plan_spec = "plans/legal.toml"
```

If validation fails you will see `Profile manifest validation failed` with specific error details, and no commands will run.

## Operations Checklist

- Keep plugin modules small and deterministic; prefer pure functions with explicit inputs.
- Use the logger provided via `runtime` for diagnostic output instead of printing.
- Version bump plugins whenever the callable's logic changes—signature digests will change.
- Store profile manifests alongside configuration so they can be pinned and reviewed like code.
- Always test profiles with `--dry-run` in CI before enabling them for production contexts.

