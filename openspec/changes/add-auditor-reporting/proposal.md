## Why
Audit outputs must be consumable by humans and machines. We need rich reporting, visualization, observability, and archival flows to communicate findings, track metrics, and preserve artifacts for future audits.

## What Changes
- Design human-readable report templates (executive summary, methodology, findings, appendices) with visualization hooks and artifact bundling.
- Implement observability for all checks (structured logs, OpenTelemetry spans, metric exports) tied to audit_run_id.
- Define storage conventions for audit artifacts (dataset, report, certificate) under immutable paths with retention policies.
- Add automation for report packaging (HTML/PDF), diff annotations vs prior plans, and distribution to governance registry.

## Impact
- Affected specs: auditor
- Affected code: report renderer, visualization bundler, observability instrumentation, artifact storage drivers, distribution hooks
