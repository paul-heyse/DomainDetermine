## ADDED Requirements
### Requirement: Prompt Template Library
The system SHALL maintain a prompt pack organized by task (mapping disambiguation, crosswalk justification, overlay proposals, self-critique, difficulty banding, judge protocols, red-team probes) with consistent naming, metadata (owner, version, retrieval policy id), and documentation.

#### Scenario: Template metadata completeness
- **WHEN** a new template is added to the library
- **THEN** the template SHALL include metadata linking to its schema, retrieval policy, owner, and changelog entry before publication

### Requirement: Schema Registry
Each prompt template SHALL have a corresponding JSON schema defining required fields, enumerations, value ranges, and citation structure. Templates MUST validate structured outputs against these schemas prior to downstream use.

#### Scenario: Schema missing
- **WHEN** a template lacks an associated schema in the registry
- **THEN** the validation pipeline SHALL fail and prevent the template from being published

### Requirement: Retrieval Policy Definitions
The prompt pack SHALL define retrieval policies specifying allowed evidence types, token budgets per source, and privacy filters. Templates MUST reference these policies to ensure grounding and compliance.

#### Scenario: Evidence outside policy
- **WHEN** a template invocation attempts to supply evidence not permitted by its retrieval policy (e.g., disallowed corpus snippets)
- **THEN** the execution framework SHALL reject the request and log a policy violation

### Requirement: Authoring Guardrails
Prompt authoring SHALL follow guidance aligned with AI-collaboration philosophy: explicit grounding with authoritative definitions, clear role separation between generation/critique/approval, deterministic sampling parameters for adjudication, and mandatory citation instructions.

#### Scenario: Missing grounding instruction
- **WHEN** a template is reviewed and lacks explicit instructions to cite provided definitions or policy text
- **THEN** the review process SHALL block publication until grounding guidance is added
