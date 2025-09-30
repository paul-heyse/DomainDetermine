## Purpose
Define the governed prompt pack surface, covering template cataloguing, schema enforcement, retrieval policies, authoring guardrails, versioning, manifest pinning, and governance event lifecycles.

## Requirements

### Requirement: Prompt Template Library
The system SHALL maintain a prompt pack organized by task (e.g., mapping disambiguation, crosswalk justification, overlay proposals, self-critique, judge protocols, red-team probes) with consistent naming, metadata (owner, version, retrieval policy ID), and documentation.

#### Scenario: Template metadata completeness
- **WHEN** a new template is added to the library
- **THEN** the template SHALL include metadata linking to its schema, retrieval policy, owner, and changelog entry before publication.

### Requirement: Schema Registry
Each prompt template SHALL have a corresponding JSON schema defining required fields, enumerations, value ranges, and citation structure. Templates MUST validate structured outputs against these schemas prior to downstream use.

#### Scenario: Schema missing
- **WHEN** a template lacks an associated schema in the registry
- **THEN** the validation pipeline SHALL fail and prevent the template from being published.

### Requirement: Retrieval Policy Definitions
The prompt pack SHALL define retrieval policies specifying allowed evidence types, token budgets per source, and privacy filters. Templates MUST reference these policies to ensure grounding and compliance.

#### Scenario: Evidence outside policy
- **WHEN** a template invocation attempts to supply evidence not permitted by its retrieval policy
- **THEN** the execution framework SHALL reject the request and log a policy violation.

### Requirement: Authoring Guardrails
Prompt authoring SHALL follow AI-collaboration guidance: explicit grounding with authoritative definitions, clear role separation between generation/critique/approval, deterministic sampling parameters for adjudication, and mandatory citation instructions.

#### Scenario: Missing grounding instruction
- **WHEN** a template is reviewed and lacks explicit instructions to cite provided definitions or policy text
- **THEN** the review process SHALL block publication until grounding guidance is added.

### Requirement: Prompt Versioning & Changelogs
Prompt templates SHALL use semantic versioning (major/minor/patch) aligned to impact classification, maintain a `CHANGELOG.md` entry per release summarising motivation and expected impact metrics, and SHALL require governance approval for major changes before rollout.

#### Scenario: Semantic version bump enforced
- **WHEN** a prompt publish workflow runs
- **THEN** the version calculator SHALL compare declared change impact to the previous version, block the publish if the semantic version increment is incorrect, and require a changelog entry with owners and expected metric deltas.

#### Scenario: Missing changelog blocks publish
- **WHEN** a new prompt version is proposed without a changelog entry
- **THEN** the governance pipeline SHALL block publication until the changelog provides rationale, expected impact, and rollback plan.

### Requirement: Manifest Pinning
Governed artifacts (coverage mappings, overlay proposals, eval suites, service jobs, readiness pipelines) SHALL record the prompt template versions and hashes used to produce outputs, and the governance registry SHALL validate that referenced prompts exist and are publishable.

#### Scenario: Artifact manifest missing prompt version
- **WHEN** an artifact manifest lacks prompt pack references
- **THEN** the registry SHALL reject the publish and require prompts to be pinned with version and hash metadata.

#### Scenario: Hash mismatch detected
- **WHEN** a manifest references a prompt version but the stored hash differs from the published artifact
- **THEN** the registry SHALL fail the publish and raise an integrity alert requiring investigation.

### Requirement: Governance Events & Lifecycle
Prompt publish, rollback, waiver approval, and experimentation outcomes SHALL emit governance events including prompt ID, version, hash, approvals, and linked artifacts. Runbooks SHALL define lifecycle procedures, rollback timelines, and documentation updates.

#### Scenario: Publish event emitted
- **WHEN** a prompt version is approved and published
- **THEN** the pipeline SHALL emit a `prompt_published` governance event with prompt ID, version, hash, approvers, and related manifests.

#### Scenario: Rollback waiver tracked
- **WHEN** a prompt rollback waiver is granted
- **THEN** the governance registry SHALL record waiver metadata (owner, justification, expiry) and link it to the prompt lifecycle dashboard.
