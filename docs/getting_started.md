# Getting Started: End-to-End Workflow Guide

This guide walks you through the DomainDetermine toolchain from a clean checkout to publishing governed artifacts. It complements `AI-collaboration.md` by giving you concrete commands, example inputs, and the expected outputs at each stage.

---

## 1. Prerequisites

1. **Clone the repo** and install submodules if your project uses them.
2. **Create the environment** using micromamba (preferred):

   ```bash
   micromamba env create -p ./.venv -f environment.yml
   micromamba run -p ./.venv pip install -e .
   ```

3. **Activate** the environment when running commands:

   ```bash
   micromamba run -p ./.venv <command>
   ```

4. **Set up secrets** (OTEL endpoints, registry credentials, etc.) via your secrets manager or `.env`. Never check secrets into git.

---

## 2. Understand the Repository

* `AI-collaboration.md` – authoritative architecture & conventions.
* `docs/` – module guides and samples (e.g., `docs/mapping.md`, `docs/samples/…`).
* `openspec/changes/` – OpenSpec proposals & task lists.
* `src/DomainDetermine/` – implementation modules (KOS ingestion, mapping, governance, readiness, CLI, etc.).

Before you begin, skim **Module 1–3** sections in `AI-collaboration.md` and the relevant `docs/*.md` guides.

---

## 3. Configure the CLI Context

Most workflows run through the Typer-based CLI (`domain-determine` entrypoint). Create a context configuration to pin registry endpoints, artifact roots, and credentials.

1. Copy the example config:

   ```bash
   cp docs/samples/config/cli.example.toml ~/.config/domain_determine/config.toml
   ```

2. Edit the copy to set:
   * `artifact_root` – where JSON manifests land (`~/DomainDetermine/artifacts` works locally).
   * `registry_url` – governance registry endpoint (file:// path or service URL).
   * `credentials_ref` – secret manager reference if applicable.
3. Switch contexts or inspect them:

   ```bash
   domain-determine context list
   domain-determine context use dev
   ```

> All CLI invocations below assume `domain-determine` is on `PATH`. If not, call via `python -m DomainDetermine.cli.app ...` inside the environment.

---

## 4. Ingest a Knowledge Organization System (Module 1)

1. Prepare a source config. A minimal example is provided at `docs/samples/kos_ingestion/manifest_sample.json`.
2. Run the ingest verb:

   ```bash
   domain-determine ingest docs/samples/kos_ingestion/manifest_sample.json
   ```

   * Output: artifact `artifacts/ingest/manifest_sample.json` containing metadata about the run.
   * Optional: provide a loader plugin with `--loader <plugin-name>` if you have custom fetching logic registered via the plugin registry.

3. Snapshot the ingested data for downstream reproducibility:

   ```bash
   domain-determine snapshot eurovoc-2025-09 --source artifacts/ingest/manifest_sample.json
   ```

   This pins a snapshot ID so later modules can reference the exact KOS version.

---

## 5. Build a Coverage Plan (Module 2)

1. Author or reuse a plan specification (YAML/JSON). Store it under `configs/coverage/plan.example.yml`.
2. Execute the planner:

   ```bash
   domain-determine plan configs/coverage/plan.example.yml --snapshot eurovoc-2025-09
   ```

   The CLI writes a JSON artifact describing the planned quotas and provenance (see `artifacts/plan/plan.example.json`).

3. Audit the plan to ensure fairness, policy compliance, and structural integrity:

   ```bash
   domain-determine audit artifacts/plan/plan.example.json --plan configs/coverage/plan.example.yml
   ```

   Review warnings and blocking errors before continuing.

---

## 6. Run the Mapping Pipeline (Module 3)

1. Prepare a mapping configuration. Example structure:

   ```json
   {
     "mapping_items": "docs/samples/mapping_items.jsonl",
     "kos_snapshot_id": "eurovoc-2025-09",
     "output_root": "artifacts/mapping/batch01"
   }
   ```

2. Execute mapping in batches:

   ```bash
   domain-determine map configs/mapping/batch01.json --batch-size 100
   ```

   * Guardrails enforce max batch sizes from context policy. Use `--max-batch` cautiously.
   * Artifacts: mapping records, candidate logs, and crosswalk proposals under the configured output root.

3. Optional – inspect deferred items in the review queue (`review_queue` emitted in the manifest) and triage them via your reviewer workbench.

---

## 7. Calibrate the Mapping Pipeline

1. Assemble a gold file for calibration. Use the CSV in `docs/samples/mapping_calibration_samples.csv` or convert it to JSON Lines:

   ```json
   {"text": "Competition law", "expected_concept_id": "EV:1", "facets": {"domain": "competition"}}
   ```

2. Run the calibration command:

   ```bash
   domain-determine calibrate-mapping configs/mapping/batch01.json docs/samples/mapping_calibration.json
   ```

   This writes metrics (`accuracy`, `precision@1`, `recall@k`, etc.) to `artifacts/calibration/batch01.json`.

---

## 8. Overlay Expansion (Module 4 – Optional)

If coverage gaps exist, draft an overlay config to propose new subtopics:

```bash
domain-determine expand configs/overlay/eu-competition-gaps.json
```

Review resulting proposals, run pilot annotations, and push accepted overlay nodes back into Module 1/2 flows.

---

## 9. Certify, Generate Evaluations, and Publish

1. **Certify Coverage Plan** (Module 5):

   ```bash
   domain-determine certify artifacts/audit/plan.example.report.json
   ```

   Produces a signed certification dossier.

2. **Generate Evaluation Suite** (Module 6):

   ```bash
   domain-determine evalgen configs/evals/eu-competition-suite.yml --sample 50
   ```

   Check outputs under `artifacts/evalgen/` (manifest, slice definitions, grader specs).

3. **Publish Artifacts** (Module 7):

   ```bash
   domain-determine publish MAP-000123 --channel staging
   ```

   The CLI runs preflight checks (`PreflightChecks` in `cli/safety.py <../../../src/DomainDetermine/cli/safety.py>`), requires confirmation, and writes registry events.

4. **Diff & Rollback**:

   ```bash
   domain-determine diff MAP-000122 MAP-000123
   domain-determine rollback MAP-000123 --snapshot eurovoc-2025-08 --yes
   ```

---

## 10. Ready for CI and Readiness Pipelines

* Wire `domain-determine run` with a workflow definition to orchestrate combos of the above steps.
* Integrate readiness telemetry (Module 9 in the handbook) with OpenTelemetry endpoints configured via environment variables.
* Use GitHub Actions workflows in `.github/workflows/` as a reference for CI orchestration (e.g., `readiness.yml`).

---

## 11. Mapping & Telemetry API Reference

* Mapping pipeline exports are documented in `docs/mapping.md`.
* `MappingTelemetry` sends metrics to `GovernanceEventLog` when configured. Examples exist in `tests/test_mapping_telemetry.py`.
* Sample gold datasets live under `docs/samples/` for quick experimentation.

---

## 12. Verification Checklist

1. **lint**: `ruff check src tests`
2. **format**: `black .`
3. **tests**: `pytest -q`
4. **openspec validation**: `openspec validate --strict`
5. **Readiness pipeline** (optional): `micromamba run -p ./.venv python scripts/e2e/run_readiness.py`

If all checks pass and documentation is updated, you are ready to raise a PR or publish artifacts per governance policy.

---

Need help or feedback? The `AI-collaboration.md` handbook explains module responsibilities, while `openspec/changes/*/tasks.md` lists outstanding work for each change proposal. Reach out to module DRIs listed in those documents for clarifications.
