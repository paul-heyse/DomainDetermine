## ADDED Requirements
### Requirement: Release Manifest Governance
Every production release SHALL emit a machine-readable manifest describing artifact hashes, configuration deltas, rollout window, approvals, rollback plan, and readiness evidence references, and SHALL persist the manifest in the governance registry prior to deployment.

#### Scenario: Manifest generated before release gate
- **WHEN** a release candidate passes readiness testing and reaches the deployment approval gate
- **THEN** the pipeline SHALL generate `release-manifest.json` containing artifact IDs/hashes, infra configuration deltas, referenced readiness scorecards, and rollback steps, and SHALL submit it to the governance registry for approval logging.

#### Scenario: Missing manifest blocks deployment
- **WHEN** a deployment attempt is made without an approved manifest in the governance registry
- **THEN** the CI/CD workflow SHALL fail with a `MISSING_RELEASE_MANIFEST` error and notify the release approvers channel.

### Requirement: Approval & Waiver Workflow
Production releases SHALL require sign-off from designated approvers defined in the manifest, SHALL record approvals and/or waivers in the governance registry, and SHALL block deployment if approvals are absent or waivers expired.

#### Scenario: Approval enforced at deploy step
- **WHEN** the deploy job executes
- **THEN** the workflow SHALL verify recorded approvals for all required roles (engineering, product, governance) and fail the deployment if any approval or waiver is missing or expired.

#### Scenario: Waiver audit trail
- **WHEN** a waiver is used to bypass a readiness failure
- **THEN** the manifest SHALL reference the waiver ID, and the governance registry SHALL record owner, justification, expiry, and mitigation plan.

### Requirement: Rollback Rehearsal Cadence
Teams SHALL execute rollback rehearsals at least every 30 days (or before major releases) using production-like manifests, and SHALL record outcomes and action items in the governance registry.

#### Scenario: Rehearsal overdue triggers alert
- **WHEN** the rollback rehearsal tracker detects no successful rehearsal in the past 30 days
- **THEN** the readiness pipeline SHALL fail with a `ROLLBACK_REHEARSAL_OVERDUE` status and page the release owner until remediation or waiver approval.

#### Scenario: Rehearsal manifest archived
- **WHEN** a rollback rehearsal completes
- **THEN** the pipeline SHALL archive the rehearsal manifest, outcome, and follow-up actions in the governance registry and link them in the readiness dashboard.

### Requirement: Governance Event Emission
Release lifecycle events (manifest creation, approval, deployment start/complete, rollback executed, waiver granted) SHALL emit structured governance events with trace IDs, actor, timestamp, and manifest references for auditing and observability.

#### Scenario: Deployment events logged
- **WHEN** deployment starts or finishes
- **THEN** CI/CD automation SHALL emit governance events (`release_started`, `release_completed`) including manifest ID, environment, approvers, and success/failure status, propagating the trace ID to readiness dashboards.

#### Scenario: Rollback emits incident linkage
- **WHEN** a rollback is executed
- **THEN** the automation SHALL emit a `release_rolled_back` event referencing the triggering incident ID, rollback manifest, and remediation plan, updating readiness dashboards accordingly.
