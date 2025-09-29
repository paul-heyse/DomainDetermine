## ADDED Requirements
### Requirement: Eval Suite Mission and Definition of Done
The eval blueprint generator SHALL convert coverage plan outputs into formal evaluation suites that can be executed repeatedly across models, ensuring deterministic graders, stable seeds, and auditable slice coverage tied to concept identifiers.

#### Scenario: Versioned eval suite ready for execution
- **WHEN** an evaluation suite is generated from a coverage plan
- **THEN** the suite manifest MUST include suite ID, semantic version, slice definitions, sampling logic, acceptance thresholds, model adapters, and random seeds
- **AND** deterministic graders or documented judge protocols MUST be referenced with code hashes and configuration parameters
- **AND** all suite artifacts MUST pin hashes for item sets and grader code to guarantee reproducibility

### Requirement: Module 6 Inputs and Outputs
The eval blueprint generator SHALL accept coverage plans, instruction and policy packs, and optional seed datasets or historical eval results, and SHALL emit machine-readable manifests, item schemas per task type, grader specifications, runner configuration, and a human-readable documentation pack.

#### Scenario: Consumes required inputs with provenance
- **WHEN** Module 6 receives a coverage plan, instruction pack, policy pack, and optional seed datasets
- **THEN** it MUST record provenance for each input including snapshot IDs, version tags, and hash references before generating suite artifacts

#### Scenario: Emits complete evaluation artifacts
- **WHEN** the suite generation completes
- **THEN** the system MUST produce:
  - a manifest containing suite ID, version, slice definitions, sampling logic, metric definitions, acceptance thresholds, model adapters, random seeds, and allowed tool use
  - item schemas for each task type (classification, extraction, generation, pairwise, code/agent) with bindings to coverage concept IDs and facets
  - grader specifications detailing deterministic checkers, rubric scorers, or LLM judge protocols with prompts, temperatures, references, and calibration settings
  - runner configuration capturing concurrency, retries, caching, rate limits, and sandbox policies
  - a documentation pack that explains scenarios, slices, grading behavior, and metric interpretation

#### Scenario: Artifacts are versioned and hash pinned
- **WHEN** any eval artifact is published
- **THEN** the manifest MUST include hashes for item sets, grader code, judge prompts, and configuration files, and SHALL link to the coverage plan snapshot ID
