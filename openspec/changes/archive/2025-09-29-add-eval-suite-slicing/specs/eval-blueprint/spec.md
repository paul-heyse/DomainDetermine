## ADDED Requirements
### Requirement: Suite Scaffolding and Slice Alignment
Evaluation suites SHALL be organised by scenario and test type, with slices mirroring coverage plan strata (branch, depth band, locale, difficulty, policy tags) and respecting allocated quotas.

#### Scenario: Scenario-oriented suite structure
- **GIVEN** a coverage plan and policy-configured scenarios
- **WHEN** Module 6 generates an evaluation suite
- **THEN** it MUST group items into scenarios with explicit test types and SHALL define slices that align with the original coverage strata, including branch, depth band, locale, difficulty, and policy tags

#### Scenario: Quota-respecting slice allocation
- **GIVEN** per-stratum quotas from the coverage plan
- **WHEN** the suite composer assigns item counts to slices
- **THEN** each slice MUST honor the allocated quota (or document deviations), and preference tasks MUST balance positive/negative pairings per slice

### Requirement: Item Provenance and Stability Controls
Evaluation suites SHALL maintain item provenance and stability by committing immutable item files for static suites and fixing seeds, sampling frames, and inclusion/exclusion lists for semi-dynamic suites.

#### Scenario: Static suite provenance
- **WHEN** a scenario uses static items
- **THEN** the generator MUST commit immutable item files containing inputs and expected outputs, pinned by hash within the suite manifest

#### Scenario: Semi-dynamic suite seed control
- **WHEN** a scenario samples items from a larger pool
- **THEN** the generator MUST record random seeds, sampling frames, and inclusion/exclusion lists per version so slice composition remains comparable across runs

### Requirement: Cross-Suite Consistency and Concept Isolation
The eval blueprint generator SHALL maintain a global registry of slices and metrics to ensure cross-suite consistency and SHALL enforce concept isolation between training, development, and evaluation datasets.

#### Scenario: Slice registry enforcement
- **WHEN** a new suite is generated
- **THEN** each slice MUST reference a registered slice definition (e.g., `EU competition hard`) to guarantee consistent semantics across releases

#### Scenario: Concept leakage prevention
- **WHEN** the evaluation suite is constructed
- **THEN** the generator MUST validate that concepts used for training or development are excluded from evaluation slices unless explicitly authorised, and SHALL document any exceptions with mitigation notes
