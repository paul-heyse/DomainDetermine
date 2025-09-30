# DomainDetermine CLI

The DomainDetermine CLI mirrors the core knowledge operating system workflows. Each command maps to a pipeline module and honours the configuration precedence defined in OpenSpec (`flags > env > config file`).

## Getting Started

```bash
# Preview an ingest run without writing artifacts
python -m DomainDetermine.cli.app --config config/cli.toml --dry-run ingest data/sources.json

# Execute a plan using the active context
python -m DomainDetermine.cli.app plan plans/legal-plan.toml
```

Global options:
- `--config /path/to/config.toml` – override the configuration file.
- `--context staging` – activate a named context profile.
- `--dry-run / --no-dry-run` – preview operations without mutating artifacts (defaults to enabled when `--dry-run` is passed).
- `--log-format json` – emit JSON logs (useful for CI). Rich progress is automatically disabled when JSON output is requested.

## Context Management

```bash
python -m DomainDetermine.cli.app context list
python -m DomainDetermine.cli.app context use staging
python -m DomainDetermine.cli.app context show
```

Contexts are stored in the configuration file. The CLI persists the most recent context selection under `~/.domain_determinate/context` so subsequent invocations reuse it automatically.

## Pipeline Verbs

Each command writes artifacts beneath `<artifact_root>/<verb>/` and records fingerprints for idempotency. Re-running a command with the same inputs results in a `[no-op]` message.

```bash
# Ingest sources into the active context
python -m DomainDetermine.cli.app ingest data/sources.json

# Generate a plan using a prior snapshot
python -m DomainDetermine.cli.app plan plans/q1.toml --snapshot-name snapshot-dev

# Publish an artifact to the "stable" channel
python -m DomainDetermine.cli.app publish plan-v1 --channel stable
```

Generated artifacts include the verb, subject, context, and the inputs that shaped the run. Fingerprints are stored under `<artifact_root>/.cli_state/` to guarantee deterministic behaviour.

## Logs and Progress

During interactive runs the CLI displays Rich-powered spinners. All runs write structured logs to `<artifact_root>/logs/cli.log`. When `--log-format json` is supplied, both console and file logs emit JSON, making the CLI suitable for CI workflows.

## Plugins

Teams can extend the CLI by publishing Python entry points under the `cli.plugins.*` namespaces. Use `python -m DomainDetermine.cli.app plugins list` to inspect discovered plugins. Command verbs may opt-in to plugins; for example, ingestion supports loader plugins via `--loader custom_loader`. Plugins execute inside a guarded sandbox: failures are logged and reported as `[plugin-error]` without crashing the core command.

The CLI enforces signature verification for plugins unless explicitly configured for development. Configure trust in `cli.toml`:

```toml
[plugins]
allow_unsigned = false  # set to true only for local experimentation

[plugins.signatures]
custom_loader = "sha256:4b31..."
```

`plugins list` shows trust status alongside each plugin (`trusted`, `unsigned`, `untrusted`, or `signature-mismatch`). Operators can add or override trusted signatures through `DD_TRUSTED_PLUGIN_SIGNATURES="name=sha256:..."`. Set `DD_ALLOW_UNSIGNED_PLUGINS=1` to temporarily permit unsigned plugins (not recommended outside local development). During execution the CLI captures plugin stdout/stderr and exposes an isolated `DD_PLUGIN_SANDBOX_DIR` scratch directory to limit side effects.

## Profiles

Profiles capture repeatable workflows as TOML manifests:

```toml
name = "legal-pilot"
cli_version = "0.1.0"

[[steps]]
verb = "ingest"
source = "data/legal.json"

[[steps]]
verb = "plan"
plan_spec = "plans/legal.toml"
```

Run them with `python -m DomainDetermine.cli.app profile run legal-pilot`. The CLI validates that each step references a known verb with the required arguments before execution, surfaces validation errors, previews the plan, honours global `--dry-run`, and then invokes the listed verbs sequentially.

## Safety Rails

Mutating commands (e.g., `publish`, `rollback`, `map`) enforce preflight checks configured per-context:

- **License flags** – declare required acknowledgements in `[contexts.<name>.policy].license_flags` and provide acceptances through `DD_ACCEPTED_LICENSE_FLAGS`.
- **Forbidden topics** – block sensitive subjects before execution by listing them under `policy.forbidden_topics`.
- **Resource guardrails** – `policy.max_batch_size`, `policy.default_timeout_seconds`, and `policy.rate_limit_backoff` bound workload size. Mapping runs can override the batch guardrail explicitly via `--max-batch`.
- **Confirmation prompts** – destructive verbs require confirmation unless `--yes` is supplied.

Secrets such as registry credentials must be referenced via `env:VAR` or secret-manager URIs: direct secret strings on CLI flags are rejected.
