# Readiness Programme

This playbook summarises how we keep the platform production-ready across three pillars:

1. **Deployment governance** – automated pipelines, change controls, and rehearsed rollbacks.
2. **Testing coverage** – readiness suites with measurable thresholds and auditable evidence.
3. **Observability & response** – metrics, logs, tracing, and incident procedures that close the loop.

Each pillar feeds the readiness dashboard and release scorecards surfaced in the governance registry.

## Deployment Governance

| Aspect | Expectations |
|--------|--------------|
| Pipeline stages | Build → readiness tests → staging promotion → approval gates → production rollout |
| Approvals | Designated approvers must sign releases prior to production; waivers logged in governance registry |
| Rollback drills | Monthly rehearsals required; failures block releases until remediation |
| Release manifest | JSON manifest stored per release containing artifact hashes, configuration deltas, rollout window, rollback plan |

**Operational flow**

1. Release candidate builds trigger pipeline.
2. Staging promotion generates a release manifest draft and requests approvals.
3. Approval gate enforces sign-off before production.
4. Post-release automation archives the manifest, links monitoring dashboards, and updates rollback readiness indicator.

**Checklist**

- [ ] Release manifest archived with hashes and approvers.
- [ ] Rollback rehearsal completed within 30 days.
- [ ] Change board notified with deployment summary.
- [ ] Observability runbooks updated if new metrics introduced.

### Deployment Gates

- Run `scripts/deployment/gate.py` (to be implemented) after readiness workflow.
- Gate queries governance registry for latest readiness scorecard and checks OTEL metrics (`readiness.passed`, latency, error rate, flake rate) before approving production rollouts.
- Failures emit OTEL span `deployment.gate` and block deployment until waiver signed or issues resolved.
- Decision records stored back in the registry with trace ID and scorecard reference.

## Readiness Testing Coverage

We execute layered suites before every production release.

| Suite Type | Purpose | Example Tooling |
|------------|---------|------------------|
| Unit | Module fidelity, fast feedback | `pytest -m "not integration"` |
| Integration | Ingest → plan → map → audit → eval flows | targeted `pytest` suites with fixtures |
| End-to-end | CLI + service against staging with production-like data | CLI harness, FastAPI client |
| Performance | SLA verification (P95 latency < 200 ms, queue depth, cost) | `pytest-benchmark`, `locust` |
| Security | Dependency and container scanning | `bandit`, `trivy`, `safety` |

**Threshold & escalation rules**

- Integration suite success rate ≥ 0.98; flake rate < 0.1.
- Performance SLO: service endpoints P95 < 200 ms.
- No critical/high CVEs; medium requires approved waiver.
- Any failure pages the on-call engineer and blocks release until resolved/waived.

**Scorecard artifact**

Pipelines emit `readiness-scorecard.json` capturing:

```json
{
  "release": "2025.10.01",
  "suites": [
    {"name": "integration", "status": "passed", "duration": 312.5},
    {"name": "performance", "status": "passed", "p95_latency_ms": 174}
  ],
  "waivers": [],
  "generated_at": "2025-10-01T12:00:00Z",
  "owner": "platform-readiness"
}
```

Scorecards live in the governance registry and are referenced by deployment manifests.

### CI Integration

- `.github/workflows/readiness.yml` runs nightly at 06:00 UTC and on demand via `workflow_dispatch`.
- The workflow provisions the micromamba environment, installs OTEL exporters, and launches `python -m DomainDetermine.readiness.runner` with `.github/readiness/config.yml`.
- Logs (`readiness_logs/`), scorecards (`readiness_scorecards/`), and metrics (`readiness_metrics.json`) are uploaded as GitHub artifacts for auditing.
- Secrets `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` must be configured to route telemetry; absence of these falls back to buffered metrics persisted in artifacts for manual review.
- Use `READINESS_ENVIRONMENT` to scope context (e.g., staging, preprod). downstream tooling reads the scorecard to block releases if `overall_passed` is false.

## Observability & Incident Response

| Component | Expectations |
|-----------|--------------|
| Metrics | Catalogue required signals per module: latency, error rate, quota usage, coverage, cost |
| Logging | Structured JSON logs containing `tenant`, `artifact`, `command`, `trace_id`, `span_id`, `outcome` |
| Tracing | OpenTelemetry spans around API requests, job enqueue/execute, registry + LLM calls |
| Alerts | Thresholds defined for SLO breaches, queue depth, readiness suite failures |
| Incident templates | Standard postmortem template with timeline, root cause, remediation, DRI |

### Metrics Catalogue

| Module | Key Metrics | SLO / Threshold |
|--------|-------------|-----------------|
| CLI | command_duration_ms, dry_run_rate, failure_rate | P95 < 5 s, failure rate < 2% |
| Service API | request_latency_ms, error_rate, active_sessions | P95 < 200 ms, error rate < 1% |
| Scheduler/Jobs | queue_depth, job_age_sec, retries_total | queue depth < 100, retries < 3 |
| Mapping | llm_cost_tokens, adjudication_latency, deferral_rate | cost per item < $0.05, deferral < 10% |
| Coverage Planner | plan_latency, allocation_iterations, infeasible_runs | P95 < 2 min, infeasible_runs = 0 |
| Auditor | audit_duration, certificate_failures | P95 < 10 min, failures trigger page |
| Eval Suite | slice_latency, judge_cost, pass_rate | pass_rate ≥ defined target |
| LLM Runtime | queue_delay_us, tokens_in/out, speculative_hits, cost_usd | queue delay < 250 ms, cost per request < governed threshold |

Metrics are exported via OTEL collectors; dashboards roll up per tenant and environment. Cost telemetry references the finance workbook for chargeback.

### Telemetry Wiring

- `DomainDetermine.readiness.telemetry.configure_otel()` bootstraps an OTLP metric exporter using environment variables defined in CI or runtime.
- The readiness pipeline uses `MetricsEmitter` to publish to OTEL or buffer locally when exporters are unavailable.
- Service layer telemetry (`service/telemetry.py`) shares the same collector, ensuring readiness dashboards correlate suite results with API behavior.
- Configure collectors to route shots to the observability backend (e.g., SigNoz, Prometheus + OTEL Collector, Datadog).

### Logging Schema & Retention

All readiness logs use the following JSON structure:

```json
{
  "timestamp": "2025-10-01T12:34:56.789Z",
  "tenant": "acme",
  "environment": "staging",
  "component": "cli",
  "command": "plan",
  "artifact": "plan-2025-10-01",
  "trace_id": "af01...",
  "span_id": "01ff...",
  "outcome": "ok",
  "duration_ms": 3245,
  "error": null
}
```

- Hot storage (30 days): searchable, full payload.
- Warm storage (180 days): PII fields hashed, only enums retained.
- Export/egress requires governance approval with license flags.

Sampling: 100% for readiness suite runs, 10% for healthy CLI/service traffic, 100% for warnings/errors.

### Tracing & Instrumentation

- CLI → Service: Typer commands wrap execution in `operation.execute` spans that propagate headers `x-trace-id`, `x-span-id`.
- Service API: `TelemetryMiddleware` records `http.request` span with attributes `method`, `route`, `tenant`.
- Worker jobs: `job_span("job.execute")` captures queue wait, retries, outcome; children spans include downstream LLM calls.
- LLM Provider: each `generate_json` / `judge` invocation records `llm.request` span with perf metrics (tokens, queue delay, engine hash).
- External gateways (SPARQL, registry): instrumented via `httpx` event hooks emitting `gateway.request` spans.

Traces must cover ≥95% of readiness workflows; nightly audit compares span counts vs. executions.

### Alerting & Incident Operations

Alert policies (PagerDuty):

- `readiness-suite-failed`: triggered on failed readiness pipeline → Sev2, notify platform-readiness.
- `error-budget-burn`: burn rate >2× for 60 min → Sev2, escalate to module owner.
- `queue-depth-spike`: job queue depth > 100 or job age > 15 min → Sev3.
- `llm-cost-spike`: cost per item > $0.05 for 15 min → Sev3 + finance e-mail.

On-call rotation follows a weekly cadence with backup engineer and product partner. All alerts include links to dashboards, runbooks, and recent deploy manifest.

**Incident template (`incident.md` stored in readiness folder):**

```
# Incident <ID>
- Declared: <timestamp>
- Commander: <name>
- Impact: <summary>
- Related Artifacts: <scorecards / manifests>
- Timeline:
  - 00:00 Alert fired
  - 00:05 Commander paged
  - ...
- Root Cause:
- Mitigations Applied:
- Follow-up Actions:
  - [ ] Action, owner, due date
```

Postmortems must be completed within 72 hours; action items tracked in the readiness backlog and referenced on the dashboard until resolved.

**Incident workflow**

1. Alert fires → on-call acknowledges & triages.
2. Incident commander opens shared timeline and applies readiness template.
3. Mitigation/rollback executed per playbook.
4. Postmortem published within 48 hours and archived in readiness folder; action items tracked to completion.

## Release Manifest & Gate Automation

- `python -m DomainDetermine.readiness.manifest` produces `release-manifest.json` after readiness suites complete, bundling artifacts, scorecard path, approvals, and rollback plan metadata.
- `python -m DomainDetermine.readiness.gate` evaluates the manifest against `.github/readiness/gate_config.yml` to confirm approvals, waiver policy, and rollback rehearsal recency before a deployment proceeds.
- Gate failures block the pipeline; remediation requires gathering missing approvals, re-running rollback rehearsal, or recording a governance waiver.
- `record_rehearsal_check` emits governance telemetry events so dashboards track rehearsal freshness and highlight stale releases.
- CI publishes `readiness_report.json`, scorecards, metrics, and the release manifest as build artifacts for audit trails.

**Telemetry implementation guidance**

- Instrument service-layer API with `TelemetryMiddleware` for request counts/latency.
- Wrap job handlers with `job_span()` to capture execution spans and emit log lines for status transitions.
- Export readiness metrics (suite durations, pass/fail, rollback rehearsal status) to the monitoring backend; chart on the readiness dashboard.

## Change Control

- Threshold updates require RFC, change board approval, and dashboard update.
- New readiness suites follow the readiness change request template and must integrate with the scorecard emitter.
- Post-incident action items are tracked in the readiness backlog; incomplete items block the next quarterly readiness review.

## Resources

- `openspec/specs/readiness/spec.md` – canonical requirements.
- `openspec/changes/add-readiness-*` – in-flight proposals (observability, testing).
- `docs/service_layer.md` – API for managing artifacts & jobs powering readiness automations.
- `docs/deployment_readiness.md` – detailed deployment pipeline, manifest, and rollback runbook.
