## ADDED Requirements
### Requirement: Prompt Versioning & Changelogs
Prompt templates SHALL use semantic versioning with changelog entries explaining purpose, drift metrics, and expected impact; major changes require governance approval prior to rollout.

#### Scenario: Missing changelog entry
- **WHEN** a new prompt version is proposed without a changelog entry summarizing motivation and expected impact metrics
- **THEN** the governance review SHALL block publication until the changelog is provided

### Requirement: Manifest Pinning
Governed artifacts (coverage mapping runs, crosswalk exports, overlay proposals, evaluations) SHALL record the prompt template versions and hashes used to produce outputs.

#### Scenario: Artifact manifest missing prompt version
- **WHEN** an artifact manifest lacks prompt pack references
- **THEN** the registry SHALL reject the publish and require prompts to be pinned

### Requirement: Experimentation & Rollout
New prompt versions SHALL undergo staged rollout with A/B testing capturing constraint adherence, grounding fidelity, hallucination rate, acceptance, cost, and latency metrics, with automated rollback triggers.

#### Scenario: A/B metrics regress
- **WHEN** a flighted prompt version underperforms baseline metrics beyond tolerated thresholds
- **THEN** the rollout SHALL automatically revert to the previous version and log the rollback event in governance
