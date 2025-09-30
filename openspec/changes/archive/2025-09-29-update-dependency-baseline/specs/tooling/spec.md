## ADDED Requirements

### Requirement: Dependency Management Policy
The project SHALL document a dependency management policy covering runtime packages, optional extras, and installation commands for local development and CI.

#### Scenario: Policy documented in repository
- **WHEN** a new contributor onboards
- **THEN** they SHALL find guidance in `docs/dependencies.md` describing the runtime requirements, extra bundles (`dev`, `service`, `docs`), and environment bootstrap commands (`pip install -e .[dev,service]`, micromamba instructions).

### Requirement: Optional Extras Alignment
The project SHALL maintain optional extras in `pyproject.toml` that align with the documented policy and CI workflows.

#### Scenario: Extras used by CI
- **WHEN** the CI workflow installs dependencies
- **THEN** it SHALL run `pip install -e .[dev,service]`, ensuring linting/testing tooling and service telemetry packages are available.

#### Scenario: Contributors install consistent toolchain
- **WHEN** a developer runs `pip install -e .[dev,service]`
- **THEN** the extras SHALL provide linting, testing, and observability tooling without additional manual steps.

### Requirement: Environment Definition Synchronization
Environment bootstrap scripts (e.g., `environment.yml`) SHALL reference the same extras to keep local and CI environments consistent.

#### Scenario: Micromamba environment installs extras
- **WHEN** a contributor provisions the micromamba environment
- **THEN** the `pip` section SHALL install `-e .[dev,service]`, keeping packages aligned with the documented policy.
