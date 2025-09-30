# Deployment Readiness & Telemetry Controls

This guide describes how deployment pipelines, governance registry policies, and telemetry signals work together to gate production releases.

## Pipeline Overview

```
Build → Readiness Pipeline → Staging Deploy → Approval Gate → Production Deploy → Post-Deploy Verification
```

### Build

1. Run unit + integration tests with coverage and lint gates.
2. Produce immutable artifacts (packages, containers, manifests) with signed hashes.

### Readiness Pipeline

1. Trigger `.github/workflows/readiness.yml` (nightly + manual) using micromamba environment.
2. `DomainDetermine.readiness.runner` executes suite configs from `.github/readiness/config.yml` and writes `readiness_report.json` + metrics/scorecards.
3. `DomainDetermine.readiness.manifest` assembles `release-manifest.json` combining readiness artifacts with deployment metadata (artifacts, feature flags, secrets, migrations, rollback plan).
4. `DomainDetermine.readiness.gate` validates approvals, waiver policy, and rollback rehearsal freshness before the workflow proceeds; failures block promotion until remediated.
5. When `READINESS_ENABLE_OTEL=1`, spans and metrics emit via OTEL with trace IDs referencing the release manifest.

### Staging Deploy

1. Apply manifests to staging environment using IaC (GitOps/ArgoCD or Terraform). Capture change request.
2. Verify smoke tests, database migrations, and secrets rotation. All operations logged with trace IDs.

### Approval Gate

1. Governance registry ingests scorecard, release manifest (signed + hashed), readiness metrics snapshot, and gate decision record.
2. Deployment gate service (backed by `DomainDetermine.readiness.gate`) verifies approval roster, rollback rehearsal SLA, and waiver policy before emitting a `deployment.gate` span with decision metadata.
3. Approvers sign off (approver + auditor) with reason codes. Waivers recorded if thresholds exceeded and referenced in the manifest waivers list.

### Production Deploy

1. Apply manifests to production with canary or blue/green strategy; slow-roll as needed.
2. Automatically insert deployment event into registry (`/artifacts/deploy`) with OTEL trace hyperlink.

### Post-Deploy Verification

1. Monitor OTEL dashboards for 30–60 min; ensure SLOs stable.
2. Archive post-deploy report with links to metrics dashboards, readiness scorecard, and incident timeline if triggered.

## Governance Registry Telemetry Integration

| Artifact | OTEL Signal | Notes |
|----------|-------------|-------|
| Readiness scorecard | Metric: `readiness.passed`, `readiness.duration_seconds` | Links to GH artifact + `readiness_scorecard_{run_id}.json` |
| Deployment manifest | Span: `deployment.execute` | Attributes: `deployment.environment`, `deployment.version` |
| Rollback rehearsal | Event log entry + metric `deployment.rollback_rehearsal_duration` | Failures block releases |
| LLM runtime | Metrics: `llm.queue_delay_us`, `llm.tokens_in/out`, `llm.cost_usd` | Alerts when thresholds breached; governance event `llm_observability_alert` |

Deployments are stored as governance artifacts with telemetry hooks:

- **Span:** `deployment.execute` (attributes: `deployment.environment`, `deployment.version`, `artifact.hash`, `owner`).
- **Metric:** `deployment.publish_lead_time` (seconds from readiness pass to production completion).
- **Event log:** `deployment.event` capturing status transitions and links to scorecard & manifest.

### Telemetry Schema

- Metrics are exported via OTLP; collectors route to backend (e.g., SigNoz or Prometheus + Grafana).
- Trace IDs referenced in registry manifests and readiness scorecards for full lineage.
- Logs use JSON schema with fields `artifact_id`, `change_type`, `status`, `trace_id`, `span_id`, `actor`.

## Deployment Gate Service

### Responsibilities

1. Fetch latest readiness scorecard via registry API.
2. Query OTEL metrics for key SLIs (latency, error rate, cost, readiness flake rate).
3. Enforce policy thresholds; produce decision record (`approve`, `reject`, `waiver_required`).
4. Emit OTEL span `deployment.gate` with decision attributes and reason codes.
5. Persist decision into governance registry, attaching readiness artifacts and telemetry references.

### Policy Configuration

```
policies:
  readiness_passed: true
  performance_p95_ms: < 200
  error_rate: < 0.01
  open_critical_incidents: 0
  readiness_waiver_expired: false
```

Policies can be updated via configuration repository; changes require governance approval and trigger OTEL event `deployment.policy_change`.

### Integration with CI/CD

The deployment gate is invoked after the readiness workflow and before production rollout. Example GitHub Actions snippet:

```yaml
deploy:
  needs: [readiness]
  steps:
    - name: Evaluate deployment gate
      run: |
        python scripts/deployment/gate.py --env production --manifest artifacts/deploy.json
```

`scripts/deployment/gate.py` (future work) calls the gate service REST endpoint, evaluates policies, and exits non-zero on failure, causing the workflow to pause until waivers are granted.

## OpenTelemetry Collector & Backend

### Collector Layout

- Receivers: OTLP (gRPC), Prometheus, Filelog (optional).
- Processors: batch, resource detection, tail-sampling (span-based), attributes filtering.
- Exporters: OTLP → backend (e.g., SigNoz), logging (debug), Prometheus remote write.

### Example Collector Snippet

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

exporters:
  otlphttp:
    endpoint: https://observability.example.com/v1/metrics

service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlphttp]
```

Collectors run per environment (staging, production) with distinct OTEL resource attributes (`service.namespace`, `deployment.environment`).

## Deployment Dashboard

Key panels:

- Readiness suite status (pass/fail, run id, duration).
- Deployment frequency, lead time, change failure rate.
- Error budget burn, latency distribution, cost per deployment.
- Rollback rehearsal status and time since last rehearsal.
- Active waivers & upcoming expirations.

## Incident & Rollback Workflow

1. Alert fires → on-call acknowledges & triages.
2. Incident commander opens shared timeline and applies readiness template.
3. Mitigation/rollback executed per playbook. If triggered by LLM observability alert, coordinate with finance for cost anomalies.
4. Postmortem published within 48 hours and archived in readiness folder; action items tracked to completion.

## Runbooks & References

- `scripts/deployment/gate.py` – CLI wrapper for deployment gate service (future work).
- `docs/readiness.md` – readiness pipeline documentation.
- `docs/service_layer.md` – service API endpoints for artifacts/jobs.
- OTEL semantic conventions for CI/CD: <https://opentelemetry.io/docs/specs/semconv/registry/attributes/cicd/>

# Deployment Readiness Runbook

This guide explains how we shepherd a release candidate from build to production, capture evidence, and rehearse rollback. It complements the broader readiness programme documented in `docs/readiness.md`.

## Pipeline Overview

```
Build → Readiness Suites → Staging Deploy → Approval Gate → Production Deploy → Post-release checks
```

| Stage | Owner | Evidence | Failure Action |
|-------|-------|----------|----------------|
| Build & packaging | Platform Eng | Build log, artifact hashes | Stop pipeline; create incident if reproducible failure |
| Readiness suites | QA / Platform | Readiness scorecard JSON + metrics snapshot | Page readiness owners; raise waiver or fix regression |
| Staging deploy | Platform Eng | Staging manifest + smoke test log | Rollback to previous staging release |
| Approval gate | Change board | Signed approval record with impact summary | Deployment blocked until approvals collected |
| Production deploy | Release engineer | Release manifest (hashes, config deltas, flags, migrations) | Trigger rollback runbook |
| Post-release checks | SRE | Monitoring screenshot, `readyz` probe history, cost delta | If KPIs degraded, initiate mitigation + incident |

## Release Manifest Template

`python -m DomainDetermine.readiness.manifest --config path/to/release_config.yml --report readiness_report.json --output release-manifest.json`

```json
{
  "release": "2025.10.02",
  "generated_at": "2025-10-02T12:00:00Z",
  "artifacts": [
    {"name": "service-api", "version": "1.4.0", "hash": "sha256:..."},
    {"name": "prompt-pack", "version": "2025.10.02", "hash": "sha256:..."}
  ],
  "scorecard_path": "readiness_scorecards/run123.json",
  "readiness_run_id": "run123",
  "feature_flags": [
    {"name": "llm_overlay_v2", "rollout_plan": "5%->25%->50%", "fallback": "disable"}
  ],
  "secrets": [
    {"name": "registry-api", "version": "2025-10-01", "rotation_evidence": "s3://.../rotation.log"}
  ],
  "migrations": [
    {"id": "2025_10_02_add_indexes", "dry_run": "s3://.../dry-run.txt", "rollback": "scripts/rollback_add_indexes.sql"}
  ],
  "approvals": [
    {"role": "change-board", "actor": "alice", "timestamp": "2025-10-02T14:30:00Z"}
  ],
  "rollback_plan": {
    "trigger": "latency_p95>400ms",
    "steps": ["disable flags", "revert to release 2025.09.25"],
    "rehearsed_at": "2025-09-18T16:00:00Z"
  },
  "metadata": {
    "environment": "production"
  }
}
```

Validate the gate:

```
python -m DomainDetermine.readiness.gate \
  --manifest release-manifest.json \
  --config .github/readiness/gate_config.yml \
  --release-id rel-2025-10-02
```

The gate fails fast if approvals are missing, waivers are disallowed, or the rollback rehearsal is older than the configured `max_rehearsal_age_days`. Telemetry emitted via `record_rehearsal_check` surfaces in readiness dashboards for audit purposes.

Store manifests in the governance registry (`governance/releases/<release>.json`) and link them from dashboards.

## Rollback Procedures

1. **Detection**: Alert or KPI indicates failure.
2. **Triage (<= 5 min)**: Incident commander assigned, rollback decision recorded.
3. **Execute rollback**: Follow manifest steps. For database migrations, execute rollback script or fail-forward plan.
4. **Verification**: Re-run readiness smoke tests, check `readyz`, validate KPIs.
5. **Evidence**: Append rollback timeline, duration, outcome to incident record.
6. **Postmortem**: Publish within 48 hours; update backlog with remediation tasks.

Rehearse the rollback once per month. Record duration, participants, surprises, and ensure the rehearsal result is linked to the next production deployment record.

## Configuration & Secrets Management

- Use version-controlled configuration (`configs/<env>/<release>.toml`).
- Secrets rotate via Vault. Record secret version + rotation evidence in the manifest.
- Feature flags: stage via LaunchDarkly cohorts. Document rollout ramp and rollback triggers.
- Schema migrations: run dry-run in staging; store output + validation summary. If backward incompatible, document mitigation.

## Change Board & Approvals

| Environment | Required approvals | Notes |
|-------------|-------------------|-------|
| Staging | Release engineer | Auto-applied |
| Production | Change board representative + SRE on-call + product owner | Waivers require explicit justification |

Update the matrix within five business days when ownership changes. Keep the matrix in `governance/change-board.yaml`.

Approvals are recorded via the release CLI (`dd governance approve --release <id> --role <role>`), which appends to the manifest.

## Training & Onboarding

- **Curriculum**: Deployment overview, pipeline walkthrough, rollback rehearsal, incident template usage.
- **Completion tracking**: Log training completion in `governance/training/deployments.csv` with actor, instructor, date.
- **Re-certification**: Annual refresher; on-call engineers must complete before joining rotation.

New engineers must shadow at least one staging and one production deployment before taking lead.

## Evidence Checklist

- [ ] Release manifest stored with hashes, flags, secrets, migrations.
- [ ] Readiness scorecard attached.
- [ ] Approval log updated (change board, SRE, product).
- [ ] Rollback rehearsal within 30 days.
- [ ] Monitoring dashboard links embedded.
- [ ] Training records up to date for executing engineers.

## Related Documents

- `docs/readiness.md` – overall readiness programme.
- `docs/service_layer.md` – API powering artifact/job management.
- `openspec/specs/readiness/spec.md` – normative requirements.
