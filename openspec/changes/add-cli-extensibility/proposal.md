## Why
We need a pluggable CLI architecture so teams can add new KOS loaders, mappers, graders, and report renderers without modifying core code. Operators also request reusable command "profiles" to standardize bundles (e.g., legal pilot baseline) for repeatable workflows.

## What Changes
- Define extensibility requirements for plugin discovery (entry-point hooks) and sandboxing.
- Introduce profile manifests describing sequences of CLI commands with pinned versions and thresholds.

## Impact
- Affected specs: `cli/extensibility`
- Affected code: CLI plugin registry, sandbox loader, profile runner
