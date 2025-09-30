## MODIFIED Requirements
### Requirement: CLI Plugin Framework
The CLI SHALL support plugin discovery via entry-point registration for new KOS loaders, mappers, graders, and report renderers, executing plugins in a sandboxed environment with error isolation and trust verification. Plugins SHALL declare name, version, and description metadata. The CLI SHALL enforce a `PluginTrustPolicy` (allow_unsigned flag, signature allowlist) and SHALL block execution of plugins whose digests do not match configured signatures unless explicitly allowed for development contexts.

#### Scenario: Discover custom loader plugin
- **WHEN** an operator installs a package exposing `cli.plugins.loaders` entry-points
- **THEN** the CLI SHALL list the loader in `cli plugins list`, annotate its trust status (`trusted`, `unsigned`, `untrusted`, `signature-mismatch`), and continue even if another plugin fails to initialize, logging the error with context.

#### Scenario: Sandbox plugin execution
- **WHEN** a plugin raises an exception during execution
- **THEN** the CLI SHALL isolate the failure, emit a structured error message, capture stdout/stderr in the sandbox log, and prevent the plugin from impacting core command state; unsigned or untrusted plugins SHALL be blocked unless `allow_unsigned` is explicitly set.

#### Scenario: Signature enforcement failure
- **WHEN** a plugin’s computed digest does not match the signature allowlist entry
- **THEN** the CLI SHALL abort execution, log the mismatch with expected vs actual digests, and instruct the operator to update the trust policy before retrying.

### Requirement: CLI Profiles
The CLI SHALL accept profile manifests that describe sequences of commands with pinned versions, thresholds, and context requirements. Manifests SHALL declare `cli_version`, SHALL include all required arguments for each verb, and SHALL be validated prior to execution. The CLI SHALL provide a dry-run preview, list validation errors, and respect global `--dry-run` without executing steps.

#### Scenario: Execute profile bundle safely
- **WHEN** an operator runs `cli profile run legal-pilot-baseline`
- **THEN** the CLI SHALL validate that each step references a known verb with required arguments, show a dry-run of planned commands (including resolved file paths), and execute the sequence respecting pinned versions and thresholds, aborting if validation errors are detected.

#### Scenario: Profile validation failure reported
- **WHEN** a profile omits a required argument or references an unknown verb
- **THEN** the CLI SHALL refuse to execute the profile, enumerating validation issues (missing arguments, unexpected keys, unknown verb) and returning a non-zero exit code.
