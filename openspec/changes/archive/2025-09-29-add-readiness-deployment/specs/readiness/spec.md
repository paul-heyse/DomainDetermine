## ADDED Requirements

### Requirement: Deployment Pipeline Governance

Deployments SHALL flow through automated pipelines enforcing build, test, approval, and rollout stages with recorded evidence.

#### Scenario: Approval-gated rollout

- **WHEN** a release candidate is promoted to staging
- **THEN** the pipeline SHALL enforce sign-off from designated approvers before production rollout.

#### Scenario: Rollback rehearsal

- **WHEN** monthly operations drills occur
- **THEN** teams SHALL execute documented rollback procedures and log outcomes in the governance registry.

### Requirement: Release Documentation & Tracking

Every deployment SHALL produce a release manifest capturing changes, environment, configuration deltas, and rollback plans.

#### Scenario: Release manifest archived

- **WHEN** production rollout completes
- **THEN** the manifest with hashes, version references, and approvers SHALL be archived in the registry and linked to monitoring dashboards.

#### Scenario: Rollback readiness indicator

- **WHEN** rollback rehearsals fail or become outdated
- **THEN** the deployment readiness dashboard SHALL surface a red indicator blocking production releases until remediation occurs.
