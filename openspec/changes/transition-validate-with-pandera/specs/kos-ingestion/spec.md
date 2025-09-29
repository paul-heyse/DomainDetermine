## MODIFIED Requirements

### Requirement: Data Quality Diagnostics

The system SHALL enforce quality gates and provide diagnostics for editorial review, validating tabular structures with Pandera schemas and typed payloads with Pydantic models.

#### Scenario: SHACL validation passes

- **WHEN** a snapshot is generated
- **THEN** the system SHALL run pyshacl validation against configured shapes (e.g., prefLabel presence, language tag conformance, DAG hierarchy) and block publication on failure.

#### Scenario: Tabular integrity checks succeed

- **WHEN** a snapshot is generated
- **THEN** the system SHALL run Pandera dataframe validations verifying ID uniqueness, referential integrity, non-empty labels, and leaf flags, blocking publication if critical checks fail.

#### Scenario: Editorial diagnostics produced

- **WHEN** a snapshot is generated
- **THEN** the system SHALL output diagnostics for duplicate altLabels under a parent, conflicting mappings, suspicious definition lengths, and capitalization inconsistencies for editorial review; these SHALL be included in the manifest or accompanying report and validated against Pydantic schemas before publication.
