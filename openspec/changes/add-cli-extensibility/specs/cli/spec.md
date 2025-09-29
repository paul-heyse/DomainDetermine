## ADDED Requirements
### Requirement: CLI Plugin Framework
The CLI SHALL support plugin discovery via entry-point registration for new KOS loaders, mappers, graders, and report renderers, executing plugins in a sandboxed environment with error isolation.

#### Scenario: Discover custom loader plugin
- **WHEN** an operator installs a package exposing `cli.plugins.loaders` entry-points
- **THEN** the CLI SHALL list the loader in `cli plugins list`, load it on demand, and continue even if another plugin fails to initialize, logging the error.

#### Scenario: Sandbox plugin execution
- **WHEN** a plugin raises an exception during execution
- **THEN** the CLI SHALL isolate the failure, emit a structured error message, and prevent the plugin from impacting core command state.

### Requirement: CLI Profiles
The CLI SHALL accept profile manifests that describe sequences of commands with pinned versions, thresholds, and context requirements.

#### Scenario: Execute profile bundle safely
- **WHEN** an operator runs `cli profile run legal-pilot-baseline`
- **THEN** the CLI SHALL validate the manifest, show a dry-run of planned commands, and execute the sequence respecting the profile’s pinned versions and thresholds.
