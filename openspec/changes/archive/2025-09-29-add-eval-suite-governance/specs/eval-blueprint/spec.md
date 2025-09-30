## ADDED Requirements
### Requirement: Item Types and Grader Contracts
The eval blueprint generator SHALL define grader contracts for deterministic checks, human rubric scoring, and LLM-as-judge protocols, ensuring transparent evidence and calibration for each mode.

#### Scenario: Deterministic grader specification
- **WHEN** a suite contains classification or extraction tasks
- **THEN** the manifest MUST reference deterministic graders with explicit normalization rules, JSON schemas, tolerance windows, and attached synonym dictionaries

#### Scenario: Rubric-based human scoring with quality gates
- **WHEN** human adjudication is required
- **THEN** the suite MUST encode rubric criteria with scale anchors, capture adjudication rules, compute inter-rater agreement (κ/α) as a first-class metric, and block publication if thresholds are not met

#### Scenario: LLM judge protocol with calibration
- **WHEN** an LLM is used as a judge
- **THEN** the manifest MUST include fixed prompts, temperature, reference materials, quote requirements, calibration set details, bias probes, and the judge model/version hash

### Requirement: Metric Framework and Acceptance Criteria
Evaluation suites SHALL define per-task metrics, statistical treatment (confidence intervals, significance tests, effect sizes), and acceptance gates (per-slice, suite-level, safety blocks).

#### Scenario: Metric computation and CI reporting
- **WHEN** evaluation results are produced
- **THEN** the system MUST compute task-appropriate metrics (accuracy, EM, token-F1, pass@k, preference win-rate, rubric averages, refusal rates) and SHALL report slice-level and suite-level confidence intervals using nonparametric bootstrap methods

#### Scenario: Acceptance thresholds and safety gates
- **WHEN** metrics are aggregated
- **THEN** the suite MUST enforce per-slice thresholds (e.g., F1 ≥ 0.85 for critical slices), suite-level composite thresholds, and SHALL fail the suite if any safety slice exceeds policy violation limits regardless of other metrics

### Requirement: Runner Architecture, Telemetry, and Reporting
The runner SHALL provide provider adapters, sandboxed execution, caching, determinism controls, telemetry, and comprehensive reporting artifacts.

#### Scenario: Runner configuration and determinism
- **WHEN** the runner executes a suite
- **THEN** it MUST use provider adapters with rate limits, retries, caching keyed by (model_id, prompt_hash, params), enforce explicit random seeds, and sandbox code/agent tasks with resource/time/network limits

#### Scenario: Telemetry and logging
- **WHEN** evaluation is running
- **THEN** the runner MUST emit per-item logs (inputs, outputs, grader verdicts, scores, confidences, cost, judge rationales) and aggregation logs (slice roll-ups, CI calculations, failures), and SHALL produce OpenTelemetry spans for end-to-end timing and cost accounting

#### Scenario: Reporting and deliverables
- **WHEN** results are finalised
- **THEN** the generator MUST produce machine-readable results bundles (scores + per-item logs + manifest), slice leaderboards, failure analyses, safety reports, comparative plots, and a human-readable PRD appendix detailing sampling, grading, aggregation, and limitations

### Requirement: Governance, Trust, and Ethics
Evaluation suites SHALL enforce versioning, deprecation policies, bias and safety controls, separation of concerns, and licensing compliance.

#### Scenario: Version freezing and deprecation policy
- **WHEN** suites are published
- **THEN** the manifest MUST pin suite version, item hashes, grader code hash, judge model/version, and random seeds; any item removal MUST be documented via deprecation entries with replacement guidance

#### Scenario: Bias, safety, and red-team slices
- **WHEN** suites include fairness or safety slices
- **THEN** the generator MUST include fairness coverage by sensitive facet (where lawful), maintain red-team slices to probe policy boundaries, document outcomes, and record mitigations

#### Scenario: Access controls and licensing
- **WHEN** evaluation artifacts display labels or definitions
- **THEN** the suite MUST respect KOS licensing, redact restricted text, include license notices in reports, and ensure eval construction remains separate from model teams to avoid overfitting
