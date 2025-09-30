# Prompt Authoring Guidelines

## Ground Rules

- Always ground responses in provided evidence.
- Maintain role separation between generation, critique, and approval templates.
- Enforce determinism (temperature <= 0.1) for adjudication tasks.
- Require citations with source identifiers for all claims.

## Directory Layout

- `templates/` contains task-specific templates as `.j2` files.
- Each template has a sibling metadata file ending with `.json`.
- Schemas live in `schemas/` using the `{template_id}_{version}.schema.json` convention.
- Retrieval policies live in `policies/` using `{template_id}_{version}.policy.json`.
- Runtime manifests are stored at `runtime_manifest.json`.

## Workflow

1. Draft template with placeholders for structured data.
2. Define JSON Schema supporting guided decoding.
3. Register retrieval policy describing allowed evidence and token budgets.
4. Update the runtime manifest with template id, version, and schema references.
5. Submit template for review and update changelog.
