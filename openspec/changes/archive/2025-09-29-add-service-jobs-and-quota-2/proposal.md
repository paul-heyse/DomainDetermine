## Why
Job orchestration, quota enforcement, and telemetry are essential to prevent resource exhaustion but currently lack governed requirements.

## What Changes
- Define job lifecycle, quota policies, telemetry expectations, and governance integration.
- Implement quota manager, job runner, log streaming, retry handling, and telemetry instrumentation.
- Document alerting thresholds and governance events for quota violations.

## Impact
- Affected specs: `service/spec.md`, `governance/spec.md`
- Affected code: `src/DomainDetermine/service/{jobs,repos}.py`
- Docs: Service/governance runbooks
- Tests: Job manager/runner tests
