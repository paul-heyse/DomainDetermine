## ADDED Requirements
### Requirement: Overlay Observability Logging
The system SHALL log prompt templates, evidence payloads, LLM outputs, critiques, and vetting decisions with content hashes, latency metrics, and tenant identifiers for reproducibility.

#### Scenario: LLM proposal logged
- **WHEN** an LLM proposal is generated for an overlay candidate
- **THEN** the system SHALL record the prompt hash, evidence pack hash, response hash, model identifier, latency, and tenant in the observability backend

### Requirement: Overlay Metrics and Dashboards
The system SHALL compute and surface KPIs including proposal throughput, acceptance rate, rejection reasons, coverage gain, pilot IAA, and reviewer SLA compliance via dashboards and alerts.

#### Scenario: Acceptance rate drops below threshold
- **WHEN** the rolling acceptance rate falls below the configured threshold
- **THEN** the observability stack SHALL fire an alert to the overlay governance channel with the affected branches and reviewer workload stats

### Requirement: Overlay Risk Controls
The system SHALL enforce hallucination controls, bias/policy filters, and licensing guardrails by validating evidence citations, screening protected categories, and masking restricted content in exports.

#### Scenario: Restricted category detected
- **WHEN** a proposal targets a policy-forbidden category
- **THEN** the system SHALL reject the candidate with reason `POLICY_FORBIDDEN` and record the relevant policy clause in the audit log

### Requirement: Overlay Internationalization
The system SHALL require language tags for all labels, support jurisdiction-scoped variants, and detect cross-lingual duplicates using multilingual embeddings with human validation.

#### Scenario: Cross-lingual duplicate found
- **WHEN** multilingual duplicate detection flags two overlay nodes as semantically equivalent across languages
- **THEN** the system SHALL queue the nodes for reviewer adjudication with similarity scores and suggested canonical mapping

### Requirement: Overlay Governance Integration
The system SHALL publish observability KPIs, risk statuses, and SLA compliance into the governance registry with escalation paths and change-board workflows documented in manifests.

#### Scenario: SLA breach recorded
- **WHEN** reviewer decision time exceeds the agreed SLA
- **THEN** the governance registry SHALL log the breach, notify the escalation contact, and require sign-off before additional candidates are queued for that reviewer
