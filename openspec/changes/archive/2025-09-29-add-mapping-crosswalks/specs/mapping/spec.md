## ADDED Requirements
### Requirement: Mapping Mission and Success Criteria
The mapping system SHALL convert messy free-text topics, document spans, and stakeholder phrases into traceable links to canonical concept identifiers sourced from Module 1, and SHALL maintain cross-scheme alignments across knowledge organization systems.

#### Scenario: High precision mappings
- **WHEN** mapping items within scope are processed end-to-end
- **THEN** the system MUST achieve and report precision@1 and coverage metrics aligned with governance targets
- **AND** MUST expose reviewer-verifiable explanations for each mapping decision

#### Scenario: Versioned crosswalks
- **WHEN** cross-scheme alignments are generated or updated
- **THEN** the system MUST produce versioned crosswalk records with provenance and SHALL surface them for review prior to publication

### Requirement: Mapping Inputs and Outputs
The mapping capability SHALL ingest normalized concept data from Module 1 and mapping items with optional context, and SHALL produce append-only mapping records, candidate logs, and crosswalk assertions persisted to governed storage.

#### Scenario: Candidate ingestion
- **WHEN** the system receives concept tables and graph exports from Module 1 alongside mapping items and optional context from Module 2
- **THEN** it MUST normalize inputs, restrict candidate scope using provided facets, and prepare them for pipeline execution

#### Scenario: Artifact persistence
- **WHEN** a mapping run completes
- **THEN** the system MUST emit mapping records capturing source text, context, selected concept ID, confidence, evidence, method, timestamp, kos_snapshot_id, and coverage_plan_id
- **AND** MUST store ranked candidate logs with per-method scores and any human adjudication notes in both columnar and relational stores
- **AND** MUST queue crosswalk assertions with supporting evidence for human approval

### Requirement: System Boundary and Trust Model
The mapping system SHALL treat Module 1 as the single source of truth for concept identity and metadata, SHALL treat LLM outputs as proposals constrained to provided candidate sets, and SHALL support offline-only inference modes without external network access.

#### Scenario: Candidate source enforcement
- **WHEN** the pipeline prepares shortlisted candidates for LLM adjudication
- **THEN** it MUST ensure every candidate originates from Module 1 data and SHALL reject any attempt to introduce new concept identifiers

#### Scenario: Offline compliance
- **WHEN** a regulated project requires no-internet execution
- **THEN** the system MUST operate exclusively on vetted local corpora and cached embeddings, documenting the isolation mode in provenance metadata

### Requirement: Multi-Pass Resolution Pipeline
The mapping capability SHALL apply normalization, high-recall candidate generation, calibrated reranking, LLM-gated decision-making, and deterministic fallback policies as part of each resolution run.

#### Scenario: Text normalization stage
- **WHEN** a mapping item enters the pipeline
- **THEN** the system MUST perform Unicode normalization, case folding, language detection, tokenization/lemmatization, acronym expansion, and stopword handling prior to candidate lookup

#### Scenario: Candidate generation stage
- **WHEN** normalized text is available
- **THEN** the system MUST run lexical search, semantic retrieval with precomputed embeddings, and graph-aware expansion to assemble a high-recall candidate set, scoped by Module 2 facets

#### Scenario: Scoring and calibration stage
- **WHEN** candidates are collected
- **THEN** the system MUST combine lexical, embedding, and graph proximity scores, MAY apply cross-encoder reranking, and SHALL calibrate scores into confidence estimates before LLM adjudication

#### Scenario: LLM adjudication stage
- **WHEN** a shortlist is ready
- **THEN** the system MUST present candidates with definitions and scope notes to an LLM constrained by strict JSON schemas, SHALL require quoted evidence from provided definitions, and MUST refuse outputs containing unknown IDs

#### Scenario: Deterministic fallback stage
- **WHEN** calibrated confidence falls below threshold or near-ties are detected
- **THEN** the system MUST defer the mapping to human review, log contextual features, and enqueue the item in a reviewer queue

### Requirement: Cross-Scheme Alignment Workflow
The system SHALL leverage Module 1 mappings where available and MAY propose new crosswalks using hybrid similarity, LLM justification, and graph coherence checks, subject to human approval.

#### Scenario: Existing mapping reuse
- **WHEN** Module 1 provides explicit inter-scheme mappings for a concept
- **THEN** the system MUST reuse and reference those mappings rather than generating new ones

#### Scenario: Crosswalk proposal generation
- **WHEN** no authoritative mapping exists and evidence supports an alignment
- **THEN** the system MUST create a proposed exactMatch/closeMatch/broadMatch/narrowMatch assertion with lexical, semantic, LLM-justified, and graph coherence evidence, and MUST mark it pending human review with full provenance

### Requirement: Data Storage and Indexing
The mapping module SHALL persist analytics tables in Parquet/DuckDB, maintain relational access paths, and manage search/vector indexes per language and domain aligned to KOS snapshots.

#### Scenario: Table persistence
- **WHEN** mapping outputs are produced
- **THEN** the system MUST write `mappings`, `candidates`, and `crosswalk_proposals` tables with schema-compliant records and SHALL align each table with the relevant kos_snapshot_id

#### Scenario: Index lifecycle
- **WHEN** embeddings or search indexes are refreshed
- **THEN** the system MUST shard by language/domain, record snapshot provenance, and ensure downstream pipeline components consume the correct index version

### Requirement: Quality Controls and Metrics
The system SHALL compute intrinsic and extrinsic quality metrics, enforce guardrails for mapping validity, and expose telemetry for governance and alerting.

#### Scenario: Metric computation
- **WHEN** a mapping batch completes
- **THEN** the system MUST calculate precision@1, recall@k, coverage, ambiguity rate, deferral rate, latency, and cost per item, and SHALL publish metrics to observability channels

#### Scenario: Guardrail enforcement
- **WHEN** mapping decisions are finalized
- **THEN** the system MUST enforce edit-distance limits for exact mappings, verify definition overlap thresholds, and detect language mismatches, rejecting outputs that fail guardrails

### Requirement: Human-in-the-Loop Operations
The mapping workflow SHALL provide reviewer tooling, codified adjudication playbooks, and feedback loops for continuous improvement.

#### Scenario: Reviewer triage interface
- **WHEN** items enter human review
- **THEN** reviewers MUST be presented with input text, candidate definitions, graph context, and LLM rationales, and SHALL be able to accept, override, or annotate with structured reason codes

#### Scenario: Learning loop updates
- **WHEN** reviewers flag hard negatives or corrections
- **THEN** the system MUST capture them for updating lexical dictionaries, reranker training data, and policy guardrails

### Requirement: Performance, Governance, and Compliance
The mapping capability SHALL meet throughput targets, maintain append-only records with provenance, respect licensing restrictions, and provide auditable reports.

#### Scenario: Throughput compliance
- **WHEN** processing large mapping batches
- **THEN** the system MUST precompute embeddings, prune candidate spaces via domain facets, batch vector queries, and offload LLM adjudication to narrowed lists to satisfy performance SLOs

#### Scenario: Immutable provenance
- **WHEN** mapping outputs are recorded
- **THEN** the system MUST store records append-only, linking replacements to superseded entries, and SHALL include kos_snapshot_id, coverage_plan_id, algo_version, and llm_model_ref metadata

#### Scenario: Licensing enforcement
- **WHEN** ontologies impose redistribution limits
- **THEN** the system MUST mask restricted labels/definitions in stored artifacts and expose hashed references where necessary, documenting the applied policy

#### Scenario: Audit reporting
- **WHEN** governance requires audit trails
- **THEN** the system MUST generate signed mapping/crosswalk reports containing evidence quotes, reviewer approvals, and compliance status

## ADDED Requirements
### Requirement: Module 3 Tooling and Libraries
Implementation SHALL rely on vetted libraries for lexical search, embedding retrieval, calibration, NLP preprocessing, storage, and schema validation as listed in the project handbook.

#### Scenario: Library compliance
- **WHEN** engineering teams implement the module
- **THEN** they MUST use rapidfuzz, rank-bm25 or equivalent OpenSearch integrations, sentence-transformers, faiss or hnswlib, scikit-learn for calibration, spaCy for linguistics, pyarrow/duckdb for storage, and pydantic/jsonschema for schema enforcement unless an approved alternative is documented
