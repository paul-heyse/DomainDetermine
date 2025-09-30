## ADDED Requirements

### Requirement: Calibration Assets & Harness
Prompt packs SHALL maintain calibration datasets for each template family, including human-reviewed prompts/responses, citation references, and expected outcomes. Calibration manifests SHALL document provenance, reviewer approvals, dataset version, and licensing. Automated calibration harnesses SHALL run against these datasets during CI and before releases.

#### Scenario: Calibration manifest validated
- **WHEN** a calibration manifest is committed
- **THEN** the calibration linter SHALL verify required fields (dataset source, reviewer list, approvals, checksum) and fail CI if metadata is missing or outdated.

#### Scenario: Calibration suite blocks release
- **WHEN** a template version fails calibration harness checks
- **THEN** the publish pipeline SHALL block the release, requiring remediation or a governance-approved waiver.

### Requirement: Template Quality Metrics
Prompt templates SHALL capture runtime metrics for grounding fidelity, hallucination rate, constraint adherence, latency, cost, and acceptance rate per version and locale.

#### Scenario: Metrics recorded per invocation
- **WHEN** a template executes via CLI or service runtime
- **THEN** the system SHALL log grounding fidelity, hallucination detection, constraint adherence, latency (ms), token cost, and accept/deferral rates tagged with `template_id`, `version`, and locale.

#### Scenario: Metrics persisted to repository
- **WHEN** metrics are emitted
- **THEN** they SHALL be stored in the prompt-pack metrics repository (or downstream warehouse) within five minutes for dashboard consumption.

### Requirement: Acceptance Yardsticks
Each template SHALL define acceptance yardsticks specifying minimum/maximum thresholds for the primary metrics and use them to determine release readiness.

#### Scenario: Yardstick evaluated during calibration
- **WHEN** calibration suites run for a template version
- **THEN** the system SHALL compare captured metrics to the yardstick thresholds (e.g., grounding fidelity ≥ 0.9, hallucination rate ≤ 0.02, citation coverage ≥ 0.95) and block promotion if thresholds are not met.

#### Scenario: Yardstick metadata published
- **WHEN** a template version is published
- **THEN** its yardstick definition SHALL be serialized alongside the template manifest (JSON/YAML) and referenced in the governance registry.

### Requirement: Dashboards and Alerts
Prompt-pack quality metrics SHALL feed dashboards and alerting that highlight KPI trends, regressions, and waiver status for governance review.

#### Scenario: Dashboard updated nightly
- **WHEN** nightly readiness jobs complete
- **THEN** the dashboard SHALL refresh trend lines for acceptance rate, grounding fidelity, hallucination rate, and cost per template, flagging values outside yardstick ranges.

#### Scenario: Alert on metric regression
- **WHEN** any KPI drifts beyond its yardstick threshold for two consecutive runs
- **THEN** an alert SHALL notify the prompt-pack governance channel, create a review task, and require waiver approval for further deployments.

### Requirement: Governance Reporting
Quality metrics, yardsticks, and waiver decisions SHALL be linked to governance artifacts and review pipelines.

#### Scenario: Waiver recorded with metrics
- **WHEN** a waiver is granted to ship a template below yardstick
- **THEN** the waiver SHALL reference the specific metrics, include mitigation plans, and expire after a defined window.

#### Scenario: Review packet generated
- **WHEN** a template release candidate is prepared
- **THEN** the system SHALL generate a review packet containing recent metric trends, yardstick evaluations, open waivers, and calibration notes for governance approval meetings.
