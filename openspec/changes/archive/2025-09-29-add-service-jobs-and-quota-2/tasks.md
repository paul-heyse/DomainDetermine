## 1. Specification & Approval
- [x] 1.1 Capture job lifecycle, quota policies, telemetry, and governance integration requirements in the spec.

## 2. Implementation
- [x] 2.1 Implement quota manager checks and integrate with registry usage/limit APIs.
- [x] 2.2 Enhance job runner for retries, log streaming, and telemetry spans.
- [x] 2.3 Emit governance events and alerts for quota violations.

## 3. Documentation & Alerts
- [x] 3.1 Document quota policies, job lifecycle, and alert thresholds in service/governance runbooks.
- [x] 3.2 Configure observability dashboards for job/quota metrics.

## 4. Testing & Validation
- [x] 4.1 Add job manager/runner pytest coverage.
- [x] 4.2 Run `pytest -q` for service job modules.
- [x] 4.3 Execute `openspec validate add-service-jobs-and-quota --strict`.
