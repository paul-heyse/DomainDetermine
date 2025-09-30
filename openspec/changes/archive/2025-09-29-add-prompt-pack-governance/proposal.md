## Why
Prompt templates must be versioned, auditable, and compatible with governed artifacts. We need semantic versioning, changelog requirements, A/B testing workflows, and manifest pinning so downstream runs know exactly which template versions were used.

## What Changes
- Introduce semantic versioning and changelog standards for prompt templates (major/minor/patch with rationale).
- Define governance manifests linking prompt versions to artifacts (e.g., mapping runs, crosswalk proposals).
- Document A/B testing workflow for new template versions (flighted cohorts, metrics collection, rollback procedures).
- Integrate prompt versions with existing governance registry and event log (publish, rollback, waiver).

## Impact
- Affected specs: prompt-pack, governance
- Affected code: prompt manifest tooling, governance registry schemas, A/B experimentation scripts
