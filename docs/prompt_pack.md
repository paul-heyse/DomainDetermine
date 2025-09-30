# Prompt Pack Governance & Quality

## Versioning & Changelog

- Semantic versioning for each template (`major.minor.patch`).
- Use `domain-determine prompt bump-version` to validate bumps, compute hashes, and append to `docs/prompt_pack/CHANGELOG.md` + `releases.jsonl`.
- Changelog entries capture rationale, owners, approval list, expected metric deltas, and the computed template hash.
- Major version bumps require governance approval before rollout; the CLI enforces impact→version alignment.
- Authors SHOULD draft entries using `docs/prompt_pack/changelog_template.md` before running the CLI to ensure governance reviewers have consistent summaries.

## Manifest Pinning

- Artifacts (mapping, overlay, evals) store prompt references as `template_id:version#hash`.
- CI enforces manifest presence; publishes fail when prompts aren’t pinned or hashes mismatch prompt registry state.
- Governance registry cross-checks each reference against the prompt registry before accepting manifests.

## Experimentation Workflow

- All prompt updates ship with A/B flight configs: cohorts, metrics, stop conditions.
- Metrics include constraint adherence, grounding fidelity, hallucination rate, acceptance, latency, cost.
- Rollbacks automatically occur when regression thresholds are exceeded.

## Events & Registry

- Governance event log records `prompt_published`, `prompt_rolled_back`, and `waiver_granted` with prompt identifiers, versions, hashes, rationale, approvals, and linked manifests.
- `PromptVersionManager` emits lifecycle events via `GovernanceEventLog` and exposes helpers for rollback/waiver logging.
- Prompt registry tracks template hash, schema ID, and policy ID; governance manifests must reference registered prompt hashes.

## Calibration & Yardsticks

- `prompt_pack.calibration` maintains calibration sets per template.
- Acceptance yardsticks define minimum/maximum thresholds for key metrics. Defaults:

| Template | Version | Grounding Fidelity ≥ | Citation Coverage ≥ | Hallucination Rate ≤ | Acceptance Rate ≥ |
|----------|---------|----------------------|---------------------|----------------------|-------------------|
| mapping_decision | 1.0.0 | 0.90 | 0.95 | 0.02 | 0.80 |

- Yardsticks live in `prompt_pack.quality.DEFAULT_YARDSTICKS` and are serialized with template manifests.
- Calibration runs check yardsticks; failures block publication or generate waivers.
- Calibration manifests live under `docs/prompt_pack/calibration/<template>/<version>/manifest.json` and include reviewer approvals, dataset checksums, licensing metadata, yardstick thresholds, and expected KPI ranges.
- Datasets (`calibration.jsonl`) contain curated input/output pairs with provenance notes; the harness verifies checksums, runs warm-ups, and records deviations from yardsticks.
- `prompt_pack.calibration.load_calibration_dataset()` loads the manifest + dataset, validates checksums, and populates warm-up routines for both proposal and judge flows.

## Automated Validation

- Request builder enforces policies (allowed sources, token budgets, filtered terms).
- Responses validated against JSON Schema and citation requirements before hand-off.
- Hallucination/grounding checks log spans and highlight failures.

## Metrics, Dashboards & Alerts

- `prompt_pack.metrics` records grounding fidelity, hallucination rate, citation coverage, constraint violations, acceptance/deferral rates, latency (ms), cost (USD/token), and maintains rolling history for dashboard trend lines.
- `prompt_pack.quality` provides yardstick evaluation helpers for CI/CD and readiness pipelines.
- Nightly jobs dump `prompt-metrics-YYYY-MM-DD.json` to the warehouse; the *Prompt Quality* Looker dashboard (dashboards/prompt-quality) visualises yardstick deltas, seven-day trend lines, grounding/acceptance scatter plots, and cost/latency overlays with slicers for locale and cohort.
- Alerts: if two consecutive runs violate yardsticks, an OpsGenie alert (`PromptPack.YardstickRegression`) pages `#prompt-pack-governance`, opens a Jira review task, and requires waiver approval before further deploys. Alert payload includes template ID, metric deltas, and links to the governance record.
- Dashboard tiles link back to release manifests and governance waivers so reviewers can trace metric shifts to decision history during weekly reviews.
- Review packets include the latest 7-day trend chart, acceptance yardstick evaluation, and outstanding waivers.
- `prompt_pack.observability.QualityDashboard` renders the latest metrics + yardsticks for CLI/SRE automation, while `AlertManager` raises `Alert` objects after consecutive regressions, logs `prompt_quality_alert` governance events, and produces review payloads.

## Runtime Management

- Runtime manifest links templates to schema, policy, and token ceilings.
- Guided decoding (XGrammar/JSON Schema) ensures structured outputs.
- Warm-up routines load calibration examples to verify schema compliance before serving.
- Health probes emit warm-up status for observability dashboards.
- `PromptRuntimeManager.summary()` exposes manifest metadata and per-template warm-up state for readiness dashboards and Module 6 reviews.
- Store manifests alongside release artifacts and reference them from Module 6 eval manifests to guarantee prompt/runtime alignment.
- Call `MetricsRepository.persist()` after readiness runs to snapshot version-tagged metrics for dashboards and audits.
