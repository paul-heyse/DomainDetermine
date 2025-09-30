## Why
LLM prompts across mapping, overlay, judge, and critique flows are scattered and undocumented. We need a centralized prompt pack containing templates, schemas, retrieval policies, and guardrails so every module operates with consistent, auditable instructions aligned to AI-collaboration principles.

## What Changes
- Establish a prompt pack repository structure grouping templates by task (mapping, crosswalk justification, overlay proposals, critiques, judges, red-team) with clear naming conventions.
- Define JSON schema registry for each template, including required fields, value ranges, enumerations, and citation formats.
- Document retrieval policies specifying allowed evidence sources, token budgets, and privacy filters per template.
- Provide authoring guidelines (grounding, role separation, determinism) plus linting/validation tooling to ensure templates and schemas stay in sync.

## Impact
- Affected specs: prompt-pack
- Affected code: prompt library packaging, schema registry tooling, documentation/runbooks for templates
