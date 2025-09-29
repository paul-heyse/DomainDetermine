## Why
Overlay success depends on scalable candidate generation with strong evidence and policy compliance. We need deterministic pipelines that mine candidates, prompt LLMs with grounded context, and self-check outputs before humans review them.

## What Changes
- Implement corpus- and ontology-driven candidate mining jobs that filter against editorial rules and Module 2 coverage gaps.
- Build retrieval-augmented LLM prompting flows with structured JSON output (names, justifications, annotation prompts, difficulty) and a self-critique stage.
- Add automated vetting: duplicate detection, editorial linting, graph sanity checks, and evidence verification.
- Encode split/merge suggestions and synonym capture within structured outputs for downstream handling.

## Impact
- Affected specs: overlay
- Affected code: overlay candidate mining jobs, LLM prompt orchestration, structured-output validators, duplicate/conflict scoring utilities
