# Prompt Pack Governance Review – 2025-10-02

- **Attendees**: prompt governance (async approval via `module-7-review@example.com`), readiness lead, reliability lead.
- **Scope**: Semantic versioning requirements, changelog enforcement, manifest pinning with hashes, governance event coverage for publish/rollback/waiver flows.
- **Decisions**:
  - Adopt CLI-driven version bumps (`domain-determine prompt bump-version`) with hash computation and changelog/journal logging.
  - Require all dependent manifests to reference prompts as `template_id:version#hash`; registry blocks mismatches.
  - Emit `prompt_published`, `prompt_rolled_back`, and `waiver_granted` events with rationale, approvals, owners, and linked manifests for dashboard ingest.
- **Follow-ups**:
  - Integrate prompt reference validation into downstream deployment manifests.
  - Monitor prompt lifecycle events on governance dashboards after first release.
