# Governance Registry & Versioning Runbook

## Registry Scope

The governance registry treats the following artifact classes as first-class, versioned assets:

- KOS snapshots
- Coverage plans and diagnostics
- Mapping/crosswalk outputs
- Overlay proposals
- Evaluation suites and scorecards
- Prompt packs and readiness templates
- Release manifests and readiness scorecards
- Service run bundles and certificates

Artifacts are identified as `<class>/<tenant>/<slug>/<version>` and the registry enforces canonical manifests containing:

- Semantic version & hash (SHA-256 over canonical payload)
- Title, summary, tenant, license tag
- Policy pack hash, change reason, creator
- Upstream dependencies (IDs + hashes)
- Reviewers, approvals, waivers, environment fingerprint
- Prompt template references when applicable

## Versioning & Signing

- Semantic version logic (major/minor/patch) is calculated by `SemanticVersioner`; publish flows must declare a change impact.
- Canonical hashing uses deterministic JSON; signatures (Sigstore/GPG or shared secret) are recorded with each manifest.
- Lineage graphs are materialised for every publish; missing dependencies or mismatched hashes block publication.
- Prompt templates are published via `domain-determine prompt bump-version`, which validates semantic bumps, computes template hashes, appends to the changelog/journal, and emits governance events.
- Governance manifests reference prompts with `template_id:version#hash`; registry validation rejects missing or mismatched prompt references.
- Registry telemetry streams publish/rollback notifications via `GovernanceTelemetry.readiness_notifications()` so readiness dashboards stay synchronised with governance events.

## Prompt Lifecycle

- `PromptVersionManager.publish` registers prompt manifests, logs changelog entries, appends to `docs/prompt_pack/releases.jsonl`, and emits `prompt_published` events with rationale, approvals, owners, and related manifests.
- Rollbacks and waivers are captured via `PromptVersionManager.record_rollback` / `.record_waiver`, emitting `prompt_rolled_back` and `waiver_granted` events and linking waiver identifiers.
- Prompt authors must update `docs/prompt_pack/CHANGELOG.md` and ensure hashed references are consumed by readiness/readout manifests before shipping dependent artifacts.
- Governance dashboards consume `prompt_*` events to display lifecycle status, waivers, and rollback justifications.
- `prompt_pack.observability.AlertManager` integrates with governance review workflows by emitting task payloads for consecutive yardstick breaches so Module 7 reviewers get actionable alerts.

## Waiver Lifecycle

- Waivers capture owner, justification, mitigation plan, expiry, and advisory links.
- Waiver status is validated during publish; expired waivers block releases.
- Alerts fire seven days before expiry.

## Event Logging & Telemetry

- Governance events (`publish_*`, `rollback_*`, prompt lifecycle, service job events) are appended via `GovernanceEventLog` with signed entries.
- `GovernanceTelemetry` records publish lead time, audit failures, rollbacks, registry latency, and rollback rehearsal status.
- Readiness dashboards surface release manifest approvals, waiver state, and rehearsal freshness.

## Backups & Recovery

- Registry snapshots (artifacts + lineage) and event logs are backed up daily to secure storage.
- Quarterly recovery drills restore snapshots into staging; drill outcomes are archived in the registry.
- Disaster recovery runbook covers secret rotation, signing key management, and audit trail validation.

## Operational Workflow

1. **Ingest**: Producers submit manifests through service APIs; payloads are hashed, signed, and stored.
2. **Review**: Approvers review manifests in the registry UI and add approvals/waivers as needed.
3. **Publish**: Publish automation enforces semantic version, hash, signature, lineage, and waiver checks before logging events.
4. **Observe**: Telemetry pipelines feed dashboards with publish lead time, waiver status, and rollback rehearsals.
5. **Recover**: Backups are validated; recovery drills executed at least quarterly.

## References

- `src/DomainDetermine/governance/{registry,versioning,waivers,event_log,telemetry}.py`
- `src/DomainDetermine/readiness/manifest.py` and `readiness/gate.py`
- Readiness documentation (`docs/readiness.md`, `docs/deployment_readiness.md`)
