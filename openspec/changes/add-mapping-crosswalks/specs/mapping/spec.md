## ADDED Requirements
### Requirement: Mapping Mission & Trust Model
The mapping system SHALL convert free-text topics into canonical concept IDs using Module 1 snapshots, treating LLM outputs as proposals constrained to vetted candidate lists. New IDs SHALL never be minted without governance approval. Offline mode SHALL operate without external network calls.

#### Scenario: Candidate source enforcement
- **WHEN** the pipeline prepares candidates for LLM adjudication
- **THEN** it SHALL ensure every candidate originates from Module 1 data filtered by coverage plan facets, rejecting any unseen IDs.

### Requirement: Multi-Pass Resolution Pipeline
Mapping SHALL perform normalization (Unicode, language detection, tokenization, acronym expansion), multi-strategy candidate generation (lexical, embedding, graph expansion), scoring/calibration, LLM adjudication with schema constraints, and deterministic fallback (human review queue) when confidence thresholds are unmet.

#### Scenario: Pipeline execution
- **WHEN** a mapping item enters the system
- **THEN** it SHALL flow through normalization → candidate generation → scoring/calibration → LLM adjudication → fallback (if needed), logging fingerprints and confidence metrics at each stage.

### Requirement: Artifact Persistence & Crosswalk Workflow
Mapping outputs SHALL be stored append-only in governed storage (Parquet/DuckDB + relational tables) capturing source text, context, selected concept ID, scores, evidence, method, timestamps, snapshot IDs, coverage plan IDs, and algo versions. Crosswalk proposals SHALL include evidence and remain pending until human approval.

#### Scenario: Mapping record persisted
- **WHEN** a mapping decision is made
- **THEN** the system SHALL append a record with all provenance metadata and store ranked candidate logs plus reviewer notes if applicable.

### Requirement: Metrics & Observability
The mapping system SHALL compute metrics (precision@1, recall@k, coverage, ambiguity rate, deferral rate, latency, cost) per batch and emit telemetry to readiness dashboards. Calibration harnesses SHALL maintain gold sets and evaluate performance.

#### Scenario: Metrics reported per batch
- **WHEN** a mapping batch completes
- **THEN** metrics SHALL be exported with batch IDs, dataset info, and stored for governance review.

### Requirement: Human-in-the-Loop Operations
Items below confidence thresholds SHALL be enqueued for human review with full context, candidate evidence, and reason codes. Reviewer decisions SHALL feed back into calibration datasets, lexical dictionaries, and guardrail policies.

#### Scenario: Reviewer triage
- **WHEN** an item is deferred to human review
- **THEN** reviewers SHALL see input text, candidate definitions, graph context, and LLM rationale, and SHALL record accept/override decisions with structured reason codes.
