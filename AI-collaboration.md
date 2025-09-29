Below is a single, comprehensive **Project & Implementation Handbook** for AI programming agents working on this initiative. It captures the **context**, **architecture**, **module‑by‑module plans**, **data contracts**, **governance**, and the **engineering conventions** you must follow. Treat this as the source of truth for how to build, run, and evolve the system.

---

# 0) Executive summary

**Goal:** Turn high‑level domain asks (“improve X”) into **concrete, auditable topic sets** that power data creation and evaluation for AI labs. We do this by ingesting authoritative **knowledge organization systems (KOS)** (taxonomies/thesauri/ontologies), planning **coverage** with quotas, mapping messy inputs to **stable concept IDs**, extending coverage safely with a curated **overlay**, certifying plans, and generating **eval blueprints** (“evals as PRD”). Everything is **versioned, diffable, and reproducible**.

**Primary outputs:**

* A **Coverage Plan** (concept IDs × facets × quotas) tied to a frozen KOS snapshot.
* A **Mapping record set** (free text → IDs) with evidence and confidence.
* An auditable **Overlay scheme** for new, reviewer‑approved subtopics.
* A **Coverage Certificate** (pass/fail gates, fairness metrics).
* A versioned **Eval Suite** (slices, items/frames, graders, thresholds).
* A signed **Run Bundle** for each evaluation execution.

**Non‑goals:** Training models; proprietary labeling tools; long‑term storage of client data beyond contractual retention; bypassing domain licensing.

---

# 1) Context & operating principles

* **Open‑box:** We maximize transparency—stable IDs, explicit quotas, reviewable prompts, explainable mapping rationales, and reproducible evals.
* **Standards‑first:** Prefer SKOS/RDF/OWL KOS; formalize deliverables as versioned artifacts with manifests.
* **Human‑in‑the‑loop at the right points:** LLMs propose; humans approve for structural changes and policy‑sensitive calls.
* **Evals as PRD:** Private evals drive scope and iteration; coverage and slices map directly to concept IDs.

---

# 2) Architecture overview (mental model)

**Flow:** *Ingest KOS → Normalize → Plan Coverage → Map Topics → Expand Overlay (optional) → Audit & Certify → Generate Eval Suite → Run Evals & Report → Govern & Version.*

**Cross‑cutting services:** Governance registry (Module 7), CLI & API, Prompt Pack, Reviewer Workbench, Telemetry/Cost.

Artifacts carry **linkage**: each pins upstream versions (e.g., Coverage Plan → KOS snapshot; Eval Suite → Coverage Plan + graders).

---

# 3) Modules (what to build and how to operate)

## Module 1 — KOS Ingestion & Graph Service

**Mission:** Load SKOS/OWL/OBO KOS, normalize to a canonical concept model, expose fast traversal/search, and emit flattened tables for analytics.

**Core responsibilities**

* Parse SKOS/RDF (via rdflib), OWL (owlready2), OBO (pronto/obonet).
* Normalize: IDs, labels (pref/alt, per language), definitions/scope notes, broader/narrower edges, mappings (exact/close/broad/narrow), provenance (source, version, license).
* Store: (a) graph store for semantic queries; (b) columnar tables (Parquet/DuckDB) for joins/analytics.
* Expose: subtree, leaves, siblings, path‑to‑root, label search, mapping lookups.
* Validate: SHACL shape checks; tabular QA (uniqueness, referential integrity).
* Index: fuzzy search (rapidfuzz), optional vector search (sentence‑transformers + faiss); mark vectors **non‑authoritative**.

**Outputs**

* **KOS snapshot**: graph + tables + manifest (hashes, version, license).
* Precomputed depth/leaf flags and branch sizes.

**Operational notes**

* Respect license ACLs; mask restricted fields in exports.
* Cache SPARQL results; memoize hot subtrees.

---

## Module 2 — Coverage Planner & Sampler

**Mission:** Convert a concept subtree + constraints into an **auditable Coverage Plan** (strata + quotas) ready for task/eval generation.

**Inputs**

* Concept frame (from Module 1), facets (locale, language, difficulty, modality…), total budget, fairness floors/ceilings, policy filters, optional observed prevalence.

**Responsibilities**

* Define **strata** (e.g., concept‑branch × depth‑band × locale × difficulty).
* Allocate **quotas**: uniform, proportional, Neyman (variance‑aware), cost‑constrained (OR‑Tools/PuLP), with deterministic rounding.
* Reduce factor explosion via **pairwise/t‑wise** combinatorial designs (allpairspy).
* Apply filters (forbidden topics, deprecated nodes) and fairness floors; record rationale.

**Outputs**

* **Coverage Plan** table (+ data dictionary), allocation report, and plan manifest (pins KOS snapshot, methods, thresholds).

**Operational notes**

* Use DuckDB over Parquet for speed; precompute branch statistics.
* Keep plan diffs human‑readable (added/removed strata, quota deltas).

---

## Module 3 — Mapping & Crosswalks

**Mission:** Map free‑text topics or document spans to **canonical concept IDs**; maintain cross‑scheme alignments.

**Inputs**

* Candidate concept universe (Module 1) optionally narrowed by Coverage facets; mapping items (topics/spans) + context.

**Responsibilities**

* Multi‑pass resolver: lexical (rapidfuzz/BM25), semantic (embeddings + ANN), graph‑aware expansion.
* Rerank and calibrate confidence; **LLM‑gated** final choice constrained to shortlisted IDs; reasons must quote provided definitions.
* Defer ambiguous/near‑tie cases to human review.
* Propose crosswalks (exact/close/broad/narrow match) with evidence; human approve.

**Outputs**

* **Mapping records** (decision + evidence + confidence), **candidate logs** (top‑k), **crosswalk proposals** (+ status).

**Operational notes**

* No open‑web at inference by default; retrieval limited to vetted evidence.
* Shard embedding indexes by language/domain; cache aggressively.

---

## Module 4 — LLM‑Assisted Taxonomy Expansion (Overlay)

**Mission:** Propose & curate **new subtopics** in an overlay scheme to close coverage gaps without mutating the base KOS.

**Inputs**

* Target parent nodes, sibling context, editorial rules, coverage gap diagnostics, optional curated domain snippets.

**Responsibilities**

* Candidate mining (keyphrases/collocations), **RAG‑grounded LLM proposals** (JSON outputs with examples, difficulty, evidence citations).
* Automated vetting: duplicate/conflict checks, editorial compliance, graph sanity, citation verification.
* Human triage → pilot annotation → approve/publish overlay nodes; maintain change log and deprecations.

**Outputs**

* **Overlay scheme** (candidate/approved/published states), plus Coverage Plan deltas.

**Operational notes**

* Overlay IDs live in our namespace; map to base concepts with SKOS links.
* Measure acceptance rate, coverage gain, and annotatability (IAA, time/item).

---

## Module 5 — Coverage Auditor & Reports

**Mission:** Certify plans before spend. Ensure structural integrity, fairness, policy compliance, and explainability.

**Responsibilities**

* Structural checks (IDs exist, non‑negative quotas, no orphan strata).
* Fairness & balance metrics (entropy, Gini, HHI) + floors/ceilings.
* Compliance: license masking, forbidden topics excluded, jurisdictional rules.
* Drift vs prior plan (delta tables, metric deltas).

**Outputs**

* **Coverage Certificate** (machine‑readable), human report (exec summary, findings, visuals), and audit dataset.

**Operational notes**

* Gates: blocking vs advisory with waivers; sign‑off captured.

---

## Module 6 — Eval Blueprint Generator (Slices & Metrics)

**Mission:** Convert the Coverage Plan into **versioned eval suites** (slices, items/frames, graders, thresholds) with reproducible protocols.

**Responsibilities**

* Suite/scenario layout; slices mirror Coverage strata; item counts per slice.
* Item types: classification, extraction, generation, pairwise preference, code/agent tasks.
* Graders: deterministic where possible (schema validation, unit tests); rubric human scoring with IAA targets; **LLM‑as‑judge** only with strict grounding/citations and calibration.
* Metrics: accuracy/F1/EM; pass@k; preference win‑rate; rubric averages + IAA; safety/refusal rates.
* Runner config: model adapters, caching, seeds, sandbox policies.

**Outputs**

* **Eval Suite manifest**, item schemas/frames, grader specs, thresholds, runner config, documentation pack.

**Operational notes**

* Pin hashes for items and grader code; any change bumps version.
* Keep “fairness slices” where appropriate and lawful.

---

## Module 7 — Governance, Versioning & Diffs

**Mission:** Make every artifact traceable, reviewable, signable, and reversible.

**Responsibilities**

* Registry of artifacts (KOS snapshots, Coverage Plans, Mappings, Overlay, Eval Suites, Prompt Pack, Run Bundles, Certificates).
* Semantic versioning + content hashes + upstream pins.
* Release lifecycle: Propose → Build → Audit → Approve → Sign → Publish.
* Diffs per artifact type; waiver workflow; rollback procedures.
* RBAC, tenancy, license enforcement; lineage graphs; event log.

**Outputs**

* Signed manifests and release notes; lineage views; diff reports.

---

# 4) Data contracts (canonical fields & expectations)

**Concept record (Module 1):**

* `concept_id` (stable IRI/CURIE), `source`, `pref_label` (per language), `alt_labels` (per language), `definition`/`scope_note` (per language), `parents` (IDs), `children` (IDs), `mappings` (type, target_scheme, target_id), `deprecated` (bool), `provenance` (source version, license), `snapshot_id`.

**Coverage Plan row (Module 2):**

* `concept_id`, `source`, `path_to_root` (list), `depth`, **facets** (e.g., `locale`, `language`, `modality`, `difficulty`…), `quota`, `allocation_method`, `policy_flags`, `notes`, `plan_version`, `kos_snapshot_id`.

**Mapping record (Module 3):**

* `source_text`/`span_ref`, `context` (facets), `target_concept_id`, `confidence`, `evidence_quotes` (with source and offsets), `method` (lexical/semantic/LLM), `timestamp`, `kos_snapshot_id`, `coverage_plan_id`, `adjudication` (if human), `decision_version`.

**Overlay node (Module 4):**

* `overlay_id`, `parent_id` (base or overlay), `labels` (per language), `definition`, `examples`, `difficulty`, `jurisdictions`, `status` (candidate/approved/published), `provenance` (prompt version, evidence pack hash), `reviewer`, `change_log`.

**Coverage Certificate (Module 5):**

* `plan_version`, `kos_snapshot_id`, `checks` (name, value, threshold, status), `fairness_metrics`, `policy_findings`, `waivers`, `signature`.

**Eval Suite manifest (Module 6):**

* `suite_id`, `suite_version`, `coverage_plan_version`, `slices` (definition, counts), `item_sources` (hashes), `graders` (type, code hash, config), `judge_protocols` (if any: model, prompts, temperature), `metrics`, `thresholds`, `seeds`, `runner_config`, `doc_hash`.

**Run Bundle:**

* `suite_version`, `model_id`, `config_hash`, `per_item_logs`, `slice_scores` (with CIs), `safety_results`, `cost`, `latency`, `signature`.

---

# 5) LLM usage policy (for all agent‑authored prompts/calls)

**General**

* **Grounding only**: prompts must **only** rely on the provided evidence (definitions, sibling labels, curated snippets). No open‑web unless explicitly enabled in context.
* **Determinism**: default `temperature` low/zero for adjudication; fix seeds; record model/version.
* **Structured outputs**: all LLM tasks produce JSON conforming to a pre‑declared schema; validate, auto‑repair if trivial, otherwise re‑ask or escalate.
* **Citations**: include verbatim quotes with source IDs/offsets for any claim used to justify a choice.
* **Safety**: do not ask the model to invent IDs or alter authoritative definitions; never bypass licensing.

**Templates (Prompt Pack)**

* Mapping disambiguation, crosswalk justification, overlay proposal, self‑critique, difficulty banding, judge protocols, red‑team probes.
* Every template has a version, schema, retrieval policy, and model routing (primary + fallback).

**Quality gates**

* Constraint adherence rate (≥ 98% first‑pass), hallucination rate (≤ 1%), grounding fidelity (≥ 95% verified quotes), acceptance rate for proposals (target ≥ 60% over time).

---

# 6) Engineering conventions & styles

**Language & runtime**

* Python ≥ 3.11. Use `poetry` or `uv` for env and locking; target Linux containers.

**Formatting & linting**

* `black` (line length 100), `ruff` (lint), `isort` (imports), `mypy` (strict, gradual).
* Docstrings: **Google style** with types and meaningful examples.

**Testing**

* `pytest` with coverage ≥ 85% on core logic; property‑based tests with `hypothesis` for mappers/planners; golden files for diffs; fixture snapshots for sample KOS.
* Testing pyramid: unit (fast), integration (DuckDB/rdflib/SPARQL), end‑to‑end (CLI flows). CI must run all.

**Commits & branches**

* Conventional Commits (`feat:`, `fix:`, `chore:`…); **trunk‑based** branching with short‑lived feature branches.
* PR checklist includes: schema changes reviewed, manifests updated, diffs generated, licenses verified.

**Observability**

* Structured logs (JSON): `ts`, `module`, `artifact_id`, `event`, `status`, `duration_ms`, `cost_tokens` (if LLM).
* OpenTelemetry traces for long jobs; metrics exported per module (throughput, error rates, cache hit rate).

**Security**

* Secrets via a manager (no plaintext); least‑privilege IAM; data residency tags in context configs; encryption at rest; PII tags on artifacts; retention/TTL enforced.

---

# 7) CLI & Service layer (how to operate)

**CLI verbs**

* `ingest`, `snapshot`, `subtree`, `plan`, `audit`, `map`, `expand`, `certify`, `evalgen`, `publish`, `diff`, `rollback`, `run`, `report`.

**Behavior**

* Idempotent runs; `--dry-run` shows planned changes; rich TTY output with progress and summaries; JSON logs for CI.
* Contexts: `dev|staging|prod` (or per‑client); registry endpoints and credentials bound to context.

**Service/API**

* FastAPI for artifact CRUD, job submission, status, and download; RBAC via JWT/mTLS; asynchronous job queue; rate limits by tenant.

---

# 8) Reviewer Workbench (HITL)

**Use‑cases:** adjudicate mappings; approve overlay proposals; review eval failures.
**UX:** side‑by‑side evidence with citations; graph context (parents/siblings); similarity panels; keyboard‑first; bulk actions; clear reason codes.
**Writes:** decisions minted as new immutable records; registry updated; diffs generated automatically.

---

# 9) Quality, SLOs & KPIs

**SLOs**

* KOS ingest snapshot → normalized tables: **P95 < 30 min** for standard dumps.
* Coverage plan build (100k nodes, 4 facets): **P95 < 10 min**.
* Mapping throughput: **≥ 50 items/sec** (batch) before LLM; **≥ 2 items/sec** including LLM gate (top‑k ≤ 5).
* Eval suite generation (slices only): **< 5 min**; run time depends on model/provider limits.

**KPIs**

* Plan fairness (entropy↑, Gini↓), zero‑quota leaves↓, ambiguous mapping rate↓, overlay acceptance rate↑, IAA in pilots≥ target, constraint‑adherence of prompts≥ target, eval flake rate↓, cost/item and cost/suite tracked.

---

# 10) Release & change management

**Lifecycle:** Propose → Build → Audit → Approve → Sign → Publish.

* Major change: board approval; Minor: dual approval; Patch: maintainer + QA.
* Artifacts are **signed**; manifests pin upstream hashes; diffs attached to the release note.
* Rollbacks are atomic; run bundles warn if upstream is rolled back.

**Waivers:** Documented with owner, expiry, mitigation; show in reports.

---

# 11) Runbooks (common end‑to‑end flows)

**A) New domain kickoff**

1. Ingest KOS; create snapshot.
2. Select root(s); export subtree(s).
3. Build Coverage Plan with constraints; review fairness; iterate.
4. Audit & certify; publish plan.
5. Generate Eval Suite; publish v1.
6. Start mapping items; triage ambiguous cases.
7. If gaps → raise overlay requests; pilot; publish overlay v1; re‑certify plan; release suite v1.1.

**B) Quarterly refresh**

1. Compare new KOS release vs snapshot (diff report).
2. Update crosswalks; assess impact on plan fairness.
3. Re‑run auditor; address warnings; publish new certificate.
4. Bump Eval Suite minor version if slices change; generate comparative scorecard template.

**C) Incident: judge drift**

1. Detect via calibration set failure; quarantine affected runs.
2. Roll judge prompt back; re‑run calibration; open change request to fix; publish patched suite.

---

# 12) Glossary (selected)

* **KOS**: Knowledge Organization System (taxonomy/thesaurus/ontology).
* **Overlay**: Our curated extension layer (new subtopics) mapped to base KOS.
* **Stratum**: A slice of coverage defined by concept/facets; unit for quotas.
* **Coverage Plan**: Table of strata with quotas and policy flags.
* **Certificate**: Signed result of Module 5; certifies plan integrity/compliance.
* **Eval Suite**: Versioned spec for evaluation (slices, items, graders).
* **Run Bundle**: Immutable record of an evaluation execution.

---

# 13) Implementation checklist (for agents)

* ✅ Use SKOS/OWL/OBO parsers; normalize to canonical fields; record provenance.
* ✅ Emit Parquet tables and a snapshot manifest with hashes and license notes.
* ✅ Build Coverage Plans with explicit allocation strategy; generate balance & fairness metrics; store plan manifest.
* ✅ Mapping: never output IDs not present in the candidate list; include evidence quotes; calibrate confidence.
* ✅ Overlay: proposals must be RAG‑grounded; pass duplicate/editorial checks; require human approval; publish overlay as separate namespace.
* ✅ Audit & Certify: pass blocking checks; attach waivers for advisories; sign certificate.
* ✅ Eval Suite: slices mirror Coverage; graders deterministic where possible; judge protocols strictly controlled; pin hashes and seeds.
* ✅ Governance: version every artifact; generate diffs; sign manifests; respect licenses; enforce RBAC and tenancy.

---

# 14) Environment & dependencies (reference)

* **Core libs:** rdflib, owlready2, pronto/obonet, SPARQLWrapper, pyshacl, pandas, pyarrow, duckdb, rapidfuzz, sentence‑transformers, faiss/hnswlib, scikit‑learn, allpairspy, OR‑Tools/PuLP, pandera, hypothesis, jsonschema/pydantic, FastAPI, Typer/Click.
* **Tooling:** black, ruff, isort, mypy, pytest, OpenTelemetry, poetry/uv, container runtime.
* **Stores:** object storage for artifacts; DuckDB/Parquet for tables; optional OpenSearch for text; optional vector store for embeddings.

---

## Final note for agents

This handbook is **complete and prescriptive**. When in doubt:

1. Prefer **deterministic, standards‑backed** methods over heuristic shortcuts.
2. Keep **humans in the loop** for structural or policy‑sensitive changes.
3. Ensure **every artifact is versioned, pinned, diffable, and signed**.
4. Treat **LLM outputs as proposals** bound by schemas and grounded evidence.
5. Never violate **licensing** or **data‑residency** constraints.

Proceed to implement modules in order, wiring each artifact into the governance registry and honoring the conventions specified here.

# 15) Exhaustive scope

Below is a deep, **narrative‑only** architecture for the first two modules. I’ll name components, responsibilities, data contracts, and operational concerns, and I’ll reference Python libraries you’d use—without showing code or pseudocode.

---

## Module 1 — **KOS Ingestion & Graph Service**

**Mission:** ingest one or more knowledge organization systems (KOS)—taxonomies, thesauri, ontologies—normalize them into a canonical model, expose fast and safe traversal/search/mapping operations, and emit flattened tables for downstream planning.

### 1) Functional scope & success criteria

* **Scope:** SKOS/RDF thesauri (e.g., EuroVoc, LCSH), OWL ontologies (e.g., FIBO, LKIF Core, SNOMED CT), and OBO ontologies (e.g., GO, ChEBI). Optional: live SPARQL endpoints (e.g., Wikidata).
* **What “good” looks like:** every concept has a stable identifier, human‑readable labels, definitions/scope notes if available, multilingual variants, normalized broader/narrower links, and cross‑scheme mappings (exactMatch/closeMatch). Queries for “subtree,” “leaves,” “path‑to‑root,” “siblings,” and “find by label/synonym” are constant‑time or cached. A flattened export exists for analytics.

### 2) External connectors (ingestion layer)

* **File parsers:**

  * SKOS/RDF: `rdflib` (Turtle, RDF/XML, JSON‑LD).
  * OWL (DL‑heavy): `owlready2` to materialize classes, object/data properties, axioms.
  * OBO: `pronto` / `obonet` for OBO Graph format.
* **Remote endpoints:** `SPARQLWrapper` for read‑only SPARQL; HTTP fetch with ETag/Last‑Modified for TTL/XML dumps; optional authentication for licensed KOS.
* **Licensing guardrails:** per‑source license metadata captured at ingest (e.g., SNOMED CT’s restrictions), with a policy switch that can **block export** of raw IDs/labels when prohibited and only allow derived statistics.

### 3) Canonical data model (concept‑centric)

Represent every source in a **uniform concept model** so consumers don’t care about native formats:

* **Concept identity:** canonical IRI (or CURIE) and a source tag (e.g., `eurovoc`, `fibo`). Maintain both **source_id** and **canonical_id** to survive re‑prefixing or mirror copies.
* **Labels:** one **preferred label** per language (SKOS `prefLabel`), unlimited alternative labels/synonyms (`altLabel`), plus acronyms and common misspellings when available.
* **Definitions & notes:** definition text (`skos:definition`, `IAO:0000115`), scope notes (`skos:scopeNote`), editorial notes if present.
* **Hierarchy:** normalized **broader/narrower** edges with directionality; limit multiple inheritance if consumers request a tree view, but preserve the DAG in the graph store.
* **Other relations:** `partOf`, `hasRole`, domain‑specific properties from OWL ontologies (captured as predicate/value pairs).
* **Mappings:** inter‑scheme links (`skos:exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch`), Wikidata QIDs when provided.
* **Language & script:** BCP‑47 language tags (`en`, `en‑GB`, `fr`, etc.) on labels/definitions.
* **Provenance:** source, version/date, licensing, original file hash, retrieval URL/commit, and ingest timestamp using `prov` fields.

All of the above is stored twice: (a) **as a graph** in an `rdflib` store for semantic queries, and (b) **as columnar tables** (Parquet via `pyarrow` / `DuckDB`) for fast analytics and joins.

### 4) Normalization pipeline

* **IRI & prefix policy:** define a prefix map (e.g., `EV:`, `FIBO:`) and ensure stable, human‑friendly CURIEs for exports.
* **Property harmonization:** map SKOS/OWL/OBO properties into the canonical slots above; handle blank nodes; lift literals out of annotations where sensible.
* **Label normalization:** case folding, Unicode NFC, punctuation trimming; keep both **raw** and **normalized** text to preserve exactness.
* **Multilingual handling:** choose a **primary locale set** (e.g., English by default) with fallbacks; expose language‑aware search/ranking.
* **Cycle detection:** detect and record cycles in broader/narrower (shouldn’t exist in well‑formed thesauri) and either break them by policy or quarantine affected nodes.
* **Deprecation & obsolescence:** mark concepts flagged as deprecated/obsolete in source ontologies; keep mappings to replacements when provided.

### 5) Storage & indexing strategy

* **Graph store:** `rdflib` graph (in‑memory during transforms; file‑backed stores if very large). For scale, consider `rdflib` + SQLite store or a remote SPARQL server for read‑heavy workloads.
* **Analytical tables:**

  * **concepts**: id, source, label_by_lang, has_definition, depth, is_leaf, is_deprecated.
  * **labels**: concept_id, text, type (pref/alt/acronym), lang.
  * **relations**: subject_id, predicate, object_id, weight/qualifier.
  * **mappings**: subject_id, mapping_type, object_scheme, object_id.
  * **paths** (optional): precomputed ancestor chains, ancestor_count, descendant_count.
* **Search indexes:**

  * Text: `rapidfuzz` for fuzzy matching; optional `whoosh`/Elasticsearch if you need full‑text.
  * Semantic: optional embedding index (`sentence‑transformers` + `faiss`) over labels/definitions for semantic lookup, kept separate and marked **non‑authoritative**.

### 6) Query & traversal service (public API surface)

* **Read primitives:**

  * Get concept by ID (with labels, definitions, mappings, provenance).
  * List children, parents, siblings; retrieve **subtree** up to a depth; list **leaves** under a node.
  * Compute **path to root** (report multiple if DAG).
  * Search by label/altLabel with language preference and fuzzy threshold.
  * Resolve mappings: given an ID in scheme A, find the exact/close match in scheme B.
* **SPARQL gateway:** a safe wrapper around `SPARQLWrapper` for parameterized queries; whitelist only **read** operations; limit result size; attach timeouts and per‑source backoff.
* **Caching:** memoize frequent traversals (e.g., subtree of high‑level domains), throttle remote endpoint calls, and cache SPARQL results keyed by the query string + source version.

### 7) Data quality & conformance

* **Shape validation:** `pyshacl` to validate SHACL shapes (e.g., “concepts must have at least one prefLabel in any language,” “broader/narrower forms a DAG”).
* **Tabular QA:** `pandera` schemas check uniqueness of IDs, referential integrity between **relations** and **concepts**, non‑empty labels, language tag sanity, no orphan nodes unless flagged.
* **Editorial checks:** duplicate altLabels under the same parent, conflicting mappings, suspicious definition lengths, and inconsistent capitalization policies.

### 8) Cross‑scheme alignment (optional but valuable)

* **Mapping sources:** trust explicit `skos:exactMatch` first. Where absent, compute candidate alignments via lexical similarity and, if allowed, semantic similarity, but keep them **provisional** until human‑approved.
* **Authority policy:** per target domain, define an order of precedence (e.g., “when FIBO and internal ontology disagree, prefer FIBO”). Record the decision in mapping metadata.
* **Drift control:** lock mapping sets by source version; a new FIBO release spawns a new mapping version and a diff report.

### 9) Observability, operations, and security

* **Logs & metrics:** structured logs for ingest, parse errors, validation failures; metrics on graph size, subtree query latency, hit/miss ratios, and SPARQL call timeouts; emit OpenTelemetry spans if using a microservice.
* **Versioning:** assign a **KOS snapshot ID** (hash of raw files + source version strings). Store snapshot manifests; tag all downstream artifacts with this ID.
* **Access control:** optional per‑source ACLs (e.g., hide labels of restricted ontologies); redact or hash sensitive annotations if license terms demand it.
* **Testing:** gold‑standard fixtures (small SKOS, OWL, OBO samples), regression snapshots for paths/subtrees, and property‑based tests for cycle detection and label normalization.

---

## Module 2 — **Coverage Planner & Sampler**

**Mission:** take a set of concepts (often a subtree from Module 1) plus business constraints, and produce an **auditable Coverage Plan**: a table of strata with quotas, facets (locale, difficulty, modality…), and notes—ready for task generation and eval design.

### 1) Inputs & configuration surface

* **Concept frame:** IDs, labels, depth, ancestor path, leaf flags, deprecation flags, and any domain attributes pulled from Module 1.
* **Facets:** locale/jurisdiction, language, modality, product line, customer segment, time period, and any policy tags (e.g., “restricted content”).
* **Constraints & targets:** total items budget, minimums per branch, fairness goals (e.g., no branch < X%), SLOs (time to first data), and **cost/effort weights** if certain strata are expensive.
* **Risk/safety rules:** forbidden concepts; jurisdictional constraints; audit requirements.
* **Historical/observed distribution (optional):** empirical frequencies from a seed corpus to inform allocation (e.g., we see more “US antitrust” than “EU state aid”).

### 2) Stratification engine (how strata are defined)

* **Stratum keys:** choose a minimal set that captures the variety you care about. Common keys are `(concept_branch, depth_band, locale, difficulty)`.
* **Tree policies:** decide where to stratify—only leaves for high specificity, or include interior nodes to ensure foundational coverage. If using a DAG, allow a concept to live in multiple strata but account for **double counting** with a de‑duplication policy.
* **Difficulty banding:** initial heuristic using structural signals (depth, fan‑out), lexical signals (term rarity, compound terms), or domain flags; optionally refine with LLM‑assisted banding and human calibration on a small pilot.

### 3) Quota allocation algorithms

Provide multiple strategies and make the choice explicit in your plan metadata:

* **Uniform allocation:** equal quota per stratum after minimum coverage constraints—useful for early pilots.
* **Proportional (by size):** allocate by number of leaf nodes or by estimated population in the source corpus.
* **Neyman allocation:** proportional to stratum variability (if you can estimate variance or error rates from pilots).
* **Cost‑constrained allocation:** incorporate per‑stratum cost/time; maximize expected information per unit cost (linear programming via `PuLP` or `OR‑Tools`).
* **Floor/ceiling & fairness:** enforce minimums per branch, cap runaway branches, prevent starvation of minority strata.
* **Rounding:** use a deterministic rounding scheme (e.g., largest remainder) to reach the exact total after integer rounding; record pre/post rounding values for transparency.

### 4) Combinatorial design (reduce factor explosion)

When multiple facets would explode the number of combinations (e.g., `jurisdiction × language × modality × difficulty`), use **pairwise or t‑wise** coverage:

* **Category‑partition modeling:** write facet value sets and constraints (e.g., invalid pairs), then generate a minimal set of combinations that cover all **pairs** (or triples) at least once using a pairwise generator (e.g., `allpairspy`).
* **Traceability:** tag each generated combination with a **coverage certificate** (e.g., “covers pair (EU, hard) and (contract_redlining, en‑GB)”), so auditors can verify.

### 5) Business logic & guardrails

* **Policy filters:** exclude deprecated concepts, forbidden topics, or strata with licensing restrictions; route them to a “quarantined” list with justification.
* **Balance against real‑world prevalence:** optionally tilt quotas toward observed prevalence using a mixing parameter (e.g., 70% proportional to prevalence, 30% uniform to ensure tail coverage).
* **Risk weighting:** over‑allocate to high‑risk or high‑impact strata (e.g., safety‑critical subtopics) and document the rationale.

### 6) LLM‑assisted refinements (with controls)

* **Banding & subtopic proposals:** ask the model to assign difficulty bands or propose missing subtopics **under strict constraints** (must map to parent concept; provide examples; reject unknown IDs).
* **Quality gates:** validate model suggestions against your canonical graph (definitions/scope notes) and require human approval for any structure‑changing action (new strata, remappings).

### 7) Outputs (authoritative artifacts)

* **Coverage Plan table** (columnar file):

  * Identifiers: concept_id, source, path‑to‑root, depth.
  * Labels: preferred label (primary language), optional localized label.
  * Facets: locale, language, modality, difficulty, other project‑specific axes.
  * Quotas: planned count, minimum, maximum, allocation method, rounding delta.
  * Controls: policy flags (restricted/allowed), risk tier, cost weight.
  * Provenance: KOS snapshot ID, allocation strategy version, timestamp, author, and any solver logs.
* **Data dictionary** documenting every column and allowed values.
* **Allocation report** explaining the method chosen, fairness constraints applied, and any deviations from proportionality.

### 8) Auditing & diagnostics

* **Coverage health:** quotas by depth, by branch, by facet; % of leaves covered; entropy of distribution; Gini coefficient to detect extreme imbalance.
* **Red flags:** strata with zero quota, branches starved below a policy threshold, orphaned concepts (no quota and no exclusion reason), heavy concentration in a small number of branches.
* **What‑if analysis:** sliders for total budget, mixing parameter (uniform vs observed), and fairness constraints that recompute quotas instantly (a small Streamlit panel is enough).

### 9) Versioning, diffs, and governance

* **Version each plan** with a semantic version and the **KOS snapshot ID**.
* **Diffs:** report added/removed concepts, quota deltas by branch, and changes in allocation method; include a human‑readable changelog (“Raised min quotas for EU competition remedies based on pilot error rates”).
* **Approvals:** capture reviewer sign‑off and attach source evidence (pilot metrics, risk memos).
* **Rollbacks:** retain the last N versions; allow rolling back both the Coverage Plan and its upstream KOS snapshot as a pair.

### 10) Performance & scale considerations

* **Batching:** perform allocation on the **flattened tables** (Parquet/DuckDB) for speed; leave semantic reasoning to Module 1.
* **Large ontologies:** for hundreds of thousands of nodes (e.g., SNOMED CT), precompute depth, leaf flags, and branch sizes once, persist as columns, and avoid on‑the‑fly traversal.
* **Parallelism:** stratification and quota allocation operate per branch/facet; parallelize at that boundary if needed.

### 11) Testing & acceptance

* **Unit tests:** deterministic allocation given fixed inputs, stable rounding to target totals, correct honoring of min/max constraints, and correct exclusion of forbidden strata.
* **Property‑based tests:** random facet grids to ensure pairwise generator respects invalid‑pair constraints and always reaches full pairwise coverage.
* **Golden reports:** snapshot a few real plans and verify diffs are human‑readable and complete.

---

## How the two modules fit together (end‑to‑end narrative)

1. **Ingest** one or more KOS in Module 1; normalize them; validate shapes; produce both a graph and a flattened concept table. Stamp everything with a **snapshot ID**.
2. **Select a root** (e.g., “competition law”) and materialize a **subtree** with labels/definitions and derived metrics (depth, leaves).
3. **Hand the subtree** to Module 2 with project constraints (budget, fairness, locale).
4. **Stratify** by the agreed facets and **allocate quotas** using the chosen strategy (e.g., proportional with fairness floors).
5. **Audit** the plan; fix imbalances; apply policy filters; re‑run.
6. **Freeze** the Coverage Plan and export the artifacts (table + report), both tagged with the KOS snapshot ID so downstream datasets and evals remain reproducible and auditable.

---

### Library quick‑reference (for implementation planning, not code)

* **Module 1:** `rdflib`, `owlready2`, `pronto`/`obonet`, `SPARQLWrapper`, `pyshacl`, `rapidfuzz`, `sentence‑transformers` + `faiss` (optional), `pandas`, `pyarrow`/`duckdb`, `pandera`.
* **Module 2:** `pandas`, `numpy`, `duckdb`, `allpairspy` (pairwise generation), `PuLP` or `OR‑Tools` (cost/fairness‑constrained allocation), `scikit‑learn` (if you compute difficulty proxies), `pandera` for tabular QA, Streamlit (optional) for what‑ifs.

This architecture gives you a **repeatable, explainable, and auditable** path from high‑level domain to specific, quota‑bearing topic sets—ready for task generation, expert staffing, and eval design.

Absolutely—here’s a **purely narrative, implementation‑level architecture** for the next two modules in the toolchain. As before, I’ll stay code‑free while being concrete about components, data contracts, safeguards, and the Python libraries you’d rely on.

---

## Module 3 — **Mapping & Crosswalks**

*(free‑text topics, document spans, or stakeholder phrases → canonical ontology IDs; plus inter‑ontology crosswalks)*

### 1) Mission & success criteria

**Mission:** turn messy inputs (user topics, doc excerpts, headings) into **traceable, auditable links** to concepts in one or more knowledge organization systems (KOS), and maintain **cross‑scheme alignments** (e.g., EuroVoc ↔ LKIF, FIBO ↔ JEL).
**Success looks like:** high **precision@1** on mappings, measurable **coverage** of in‑scope topics, **explanations** humans can verify, and stable **versioned crosswalks** with provenance.

### 2) Inputs and outputs (data contracts)

* **Inputs**

  * **Candidate space:** the normalized concept tables/graph from Module 1 (IDs, labels, altLabels/synonyms, definitions, scope notes, language tags, parent/child links, mappings like `skos:exactMatch`).
  * **Mapping items:**

    * *Topics* (short phrases from stakeholders).
    * *Document spans* (sentences/paragraphs; offsets supplied).
    * *Context* (optional): domain, jurisdiction, language, and the **Coverage Plan** slice from Module 2 (to bias disambiguation).
* **Outputs**

  * **Mapping record**: `{source_text, context_id, target_concept_id, confidence, evidence, method, timestamp, kos_snapshot_id, coverage_plan_id}`.
  * **Candidate set log**: ranked list of the top‑k candidates with scores per method (lexical, semantic, LLM), the final decision, and any human adjudication notes.
  * **Crosswalk assertion**: when mapping bridge is missing between schemes, produce a *proposed* `exactMatch/closeMatch` triple with evidence and route to human review.

*(Persist both mapping records and candidate logs in columnar storage and a relational store for queryability.)*

### 3) System boundary & trust model

* Treat **Module 1** as *source of truth* for concept identity/labels/definitions/mappings.
* Treat **LLM outputs as proposals**: never accept an ID outside the supplied candidate set; never create new “authoritative” IDs here (that belongs to Module 4).
* Maintain a **“no internet at inference”** option for regulated projects; retrieval must be from vetted local corpora.

### 4) Pipeline stages (multi‑pass resolution)

**(A) Normalization & enrichment**

* Text cleaning (Unicode normalization, case folding), language detection, tokenization/lemmatization (e.g., spaCy), acronym expansion (rule lists per domain), and stopword handling per language.
* Domain prior: use Module 2’s **facet** (e.g., “EU competition law”) to restrict the candidate concept universe up front.

**(B) Candidate generation (high recall)**

* **Lexical search** over labels and synonyms (rapid fuzzy matching, BM25/Okapi if using a text index such as Elasticsearch/OpenSearch).
* **Semantic retrieval** using precomputed embeddings for labels+definitions (e.g., `sentence-transformers`, domain‑specific models like SciBERT/SapBERT/Legal‑BERT/FinBERT; ANN index via FAISS/HNSW).
* **Graph‑aware expansion:** include parents/siblings of lexical hits to catch near‑misses; include `skos:altLabel` and multilingual variants.

**(C) Candidate scoring & reranking**

* Hybrid score combining lexical similarity, embedding similarity, and **graph proximity** (e.g., penalty for distant ancestors if a closer sibling exists).
* Optional **cross‑encoder reranker** (e.g., MS‑MARCO‑tuned models) for shortlists to sharpen precision@1.
* Calibration layer (e.g., Platt/temperature scaling) to turn raw scores into **calibrated confidence**.

**(D) LLM‑gated decision**

* Present the **shortlisted, known IDs** with their definitions/scope notes to the LLM, constrain output to a **strict JSON schema**, and ask for:

  * selected `concept_id` (must be from shortlist),
  * short **reason** quoting definition phrases,
  * **confidence** band, and
  * **alternates** (top‑k) with reasons.
* Enforce **schema validation** and **quoting discipline** (the reason must quote text present in the provided definitions); reject any unknown IDs.

**(E) Deterministic policy & fallbacks**

* If the calibrated confidence < threshold or the top two candidates are near‑ties, **defer to human** and add to a review queue.
* For repeated ambiguous strings (“bond” chemistry vs finance), add **contextual features** (document section type, parent heading, other mapped terms nearby) to bias the decision; log these features.

### 5) Cross‑scheme alignment (building crosswalks)

* Prefer explicit mappings already present in Module 1.
* When missing, allow the system to **propose** `exactMatch/closeMatch/broadMatch/narrowMatch` across schemes using a hybrid method:

  * lexical+semantic similarity between concept labels/definitions across schemes,
  * **LLM justification** constrained to citing both definitions,
  * **graph coherence** check (parents of A should align to parents of B with compatible relations).
* All proposed crosswalks are **pending** until human‑approved; track lineage, evidence excerpts, and reviewer.

### 6) Data stores & indexes

* **Analytics tables** (Parquet/DuckDB):

  * `mappings`: one row per mapping decision with all attributes and confidence.
  * `candidates`: exploded top‑k per mapping with per‑method scores.
  * `crosswalk_proposals`: proposed inter‑scheme links with evidence and status.
* **Search & vector stores**: text index for labels/defs (if using OpenSearch), ANN index for embeddings per language/domain. Keep **snapshot IDs** aligned to the KOS snapshot version.

### 7) Quality controls & metrics

* **Intrinsic**: precision@1 (on a gold set), recall@k (candidate generation), coverage of in‑scope items, ambiguous‑rate, deferral‑rate, and average latency/cost per item.
* **Extrinsic**: downstream **IAA** on reviewer adjudications; error taxonomy (e.g., sibling confusion, over‑generalization).
* **Guards**: maximum edit distance for “exact” mappings, minimum definition overlap for acceptance, multilingual mismatch detection (label language ≠ input language).

### 8) Human‑in‑the‑loop operations

* **Triage UI**: side‑by‑side view of input text, candidate definitions, graph position, and LLM rationale; accept/override; assign error codes.
* **Playbooks**: common adjudication rules (prefer leaf‑level unless instruction says otherwise; prefer domain‑specific scheme over general scheme).
* **Learning loop**: hard negatives feed a **retraining list** for lexical synonym dictionaries and the reranker.

### 9) Performance & scale

* Precompute and cache embeddings for all concept labels/definitions.
* Keep candidate space pruned by **domain facets** from Module 2; shard ANN indexes by language/domain.
* Batch mapping items for better vector store throughput; push the LLM stage only on narrowed top‑k lists.

### 10) Governance, versioning, compliance

* **Immutability:** mapping decisions are append‑only; corrections are new rows referencing superseded ones.
* **Provenance:** every mapping carries `kos_snapshot_id`, `coverage_plan_id`, `algo_version`, and `llm_model_ref`.
* **Licensing:** if certain ontologies restrict redistribution, store internal IDs and references, not full text; expose **hashes** of definitions in evidence logs when necessary.
* **Audits:** export a signed report of mappings with evidence quotes and reviewer approvals.

**Key Python libraries**: `rapidfuzz`, `rank-bm25` or OpenSearch/Elasticsearch client, `sentence-transformers`, `faiss`/`hnswlib`, `scikit-learn` (calibration), `spacy`, `pyarrow`/`duckdb`, `pydantic`/`jsonschema`, optional `langdetect`/fastText for language ID.

---

## Module 4 — **LLM‑Assisted Taxonomy Expansion**

*(propose missing subtopics, splits/merges, synonyms, and difficulty bands—safely and with evidence)*

### 1) Mission & success criteria

**Mission:** extend a base KOS with **well‑justified, annotatable subtopics** that improve coverage where your plan (Module 2) shows gaps—without corrupting the authoritative ontology.
**Success looks like:** high **acceptance rate** of proposals by domain reviewers, measurable **coverage gains**, **no duplication/conflicts** with existing nodes, and clean **overlay governance**.

### 2) Architectural stance: overlay, not overwrite

* Maintain an **extension layer** (your organization’s scheme) that references the base KOS via `skos:broader`/`narrower` and `skos:closeMatch/exactMatch` when appropriate.
* Keep each proposed node in **candidate → approved → published** states, with reviewer identity and timestamps.
* Never mint IDs inside licensed schemes; mint them in your overlay namespace and **map** to base where appropriate.

### 3) Inputs & evidence pack

* **Target parent concept(s)** from Module 1 with:

  * preferred/alt labels, definitions, scope notes, siblings list, editorial rules (if provided by the scheme).
* **Coverage diagnostics** from Module 2 showing under‑covered branches and desired facets (e.g., locale, modality).
* **Domain corpora** (optional but powerful): representative documents (prospectuses, contracts, clinical notes) for **retrieval‑augmented prompting** to anchor proposals in reality.
* **Policy guardrails**: forbidden categories, jurisdictional constraints, naming conventions.

### 4) Proposal workflows (how a new subtopic is born)

**(A) Candidate mining (non‑LLM sources)**

* **Corpus‑driven**: keyphrase extraction (YAKE/KeyBERT), collocation mining, frequent n‑grams within a branch; filter by POS patterns and stoplists.
* **Ontology‑driven**: siblings analysis (semantic clustering of siblings’ definitions) to spot “holes” (e.g., missing common subtype).
* **External KOS**: lookups in adjacent schemes (e.g., JEL under a FIBO branch) to import structured ideas, not terms.

**(B) LLM proposal generation**

* **Retrieval‑augmented prompts**: pass the parent’s definitions, sibling labels, editorial rules, and **curated corpus snippets**; ask for:

  * candidate *names*,
  * **justifications** (with **inline citations to provided snippets**),
  * **three example annotation prompts** per candidate,
  * **difficulty band** with objective criteria,
  * suggested **nearest existing node** (if a split/merge is more appropriate).
* **Constrained output**: strict JSON schema; controlled vocabularies (difficulty levels, allowed jurisdictions); grammar‑constrained decoding or structured‑output frameworks to prevent drift.
* **Self‑critique pass**: run a second LLM check to test **non‑overlap**, **annotatability** (“can a reviewer decide with the text at hand?”), and **policy compliance**. The critique must reference rules verbatim.

**(C) Automated vetting**

* **Duplicate detection**: fuzzy match and embedding similarity against parent’s children and synonyms; thresholded rejection.
* **Editorial policy checks**: naming style (e.g., noun phrases), maximum length, no ambiguous modifiers; language availability if multilingual is required.
* **Graph sanity**: no cycles; cardinality rules (e.g., not more than N new children per batch without review).
* **Evidence validation**: ensure every claim’s citation actually appears in the supplied evidence pack; reject hallucinated citations.

**(D) Human review & pilot**

* **Triaging UI**: show proposal, evidence quotes, sibling list, and “nearest neighbor” with distances; quick accept/revise/reject actions with reason codes.
* **Pilot annotation**: sample 10–30 real items per accepted candidate; measure **IAA** and **throughput**; auto‑demote candidates with poor annotatability.
* **Finalize**: accepted nodes get overlay IDs, are published to the extension scheme, and are added to Module 2’s **Coverage Plan** with initial quotas.

### 5) Managing splits, merges, and synonyms

* **Split**: propose children under an existing too‑broad node; keep the parent as a **non‑leaf** category; add migration rules for existing mapped data.
* **Merge**: propose deprecating near‑duplicate leaves and redirecting to a canonical node (keep `skos:exactMatch` from deprecated → canonical).
* **Synonyms**: when LLM suggests alternative names, add as `altLabel` with language tags; run **conflict checks** to avoid altLabel collisions.

### 6) Data model for the overlay

* **Extension node**: overlay ID, preferred label(s), altLabels, parent (base or overlay), definition (short and long), examples, difficulty, jurisdiction tags, provenance (LLM prompt hash, evidence sources), reviewer, decision.
* **Change log**: reason for change (coverage gap, pilot failure), impacted strata/quotas, deprecation links.
* **Publication manifest**: versioned release of the overlay (semantic version + base KOS snapshot IDs).

### 7) Quality metrics & gates

* **Pre‑publication gates**:

  * duplicate & conflict score below thresholds,
  * editorial compliance (naming rules),
  * evidence presence and verification,
  * reviewer approval.
* **Post‑publication metrics**:

  * **Acceptance rate** of proposals,
  * **Coverage gain** (additional % of corpus items now mappable),
  * **Annotatability** (IAA, time/item),
  * **Downstream win rate** on eval slices tied to the new nodes.

### 8) Risk controls & safety

* **Hallucination controls**: retrieval‑only context, **no open web** in prompts unless sanctioned; require **verbatim quotes** of definitions/evidence with offsets.
* **Bias & compliance**: prohibit protected‑attribute categories unless explicitly required; pass proposals through policy filters; require legal counsel review for sensitive domains.
* **Licensing**: if the base KOS is restricted, store only overlay nodes and **pointers**; never redistribute restricted definitions; keep license metadata with every proposal.

### 9) Internationalization & jurisdictional variants

* Require language tags for labels; ensure **at least one** target language is present for publication.
* Allow **jurisdiction‑scoped children** when a parent concept manifests differently by region (e.g., “Merger control thresholds — EU” vs “— US”).
* Use cross‑lingual embeddings and bilingual lexicons to detect duplicates across languages; require human validation for translations.

### 10) Integration with Modules 1–3

* **Reads**: uses Module 1’s graph (definitions, siblings, editorial rules) and Module 2’s coverage gaps.
* **Writes**: publishes an **overlay scheme** (SKOS/OWL) back into Module 1’s store (as a separate namespace) and emits **Coverage Plan deltas** for Module 2 (new rows + reallocation suggestions).
* **Feedback loop**: Module 3’s ambiguous mappings trigger **expansion requests**; accepted overlay nodes reduce Module 3’s ambiguity over time.

### 11) Observability & governance

* **Prompts & outputs**: log prompt templates, evidence payloads, LLM outputs, and critiques with hashes for reproducibility.
* **Dashboards**: proposal throughput, acceptance rate by reviewer, top reasons for rejection, coverage gains by branch, IAA in pilot tasks.
* **Review SLAs**: time‑to‑decision for candidates; escalation paths; change‑management board for large structural edits.

**Key Python libraries**: `sentence-transformers` (embeddings), `faiss`/`hnswlib` (ANN), `rapidfuzz`/`textdistance` (duplicate checks), `spacy` (linguistics), `keybert`/`yake` (term mining), `pydantic`/`jsonschema` (structured outputs), **structured‑output frameworks** (e.g., Guardrails/outlines/jsonformer) for grammar‑constrained LLM returns, `pyarrow`/`duckdb` (storage), `matplotlib/plotly/Streamlit` (light dashboards), `scikit-learn` (clustering & simple QC models), `krippendorff`/`scikit‑learn` for IAA.

---

## How Modules 3 & 4 cooperate in practice

1. **Module 3** maps your incoming phrases/spans to existing IDs with strong guardrails and **explanations**.
2. **Ambiguities and low‑recall areas** are automatically **flagged** and passed to **Module 4** as *expansion requests* with concrete evidence (topics, failing spans, sibling sets).
3. **Module 4** proposes, vets, and pilots new subtopics in an **overlay** until accepted; once published, Module 1 ingests the overlay and Module 2 updates the **Coverage Plan**.
4. **Module 3** immediately benefits: mappings that used to defer now resolve cleanly to the newly approved overlay nodes, with higher precision and fewer human touches.

This keeps the whole pipeline **auditable, explainable, and evolvable**—and it mirrors the “open‑box” expectations you’ll see from top AI labs: traceable IDs, explicit coverage decisions, and verifiable human oversight at the right points.

Absolutely—here’s a **purely narrative, implementation‑level architecture** for the next two modules in the toolkit. As before, I’ll stay code‑free while being concrete about components, data contracts, QA, governance, and the Python libraries you’d lean on.

---

## Module 5 — **Coverage Auditor & Reports**

*(prove that your Coverage Plan is balanced, policy‑compliant, and auditable before anyone spends on data)*

### 1) Mission & “definition of done”

**Mission:** validate that the Coverage Plan produced in Module 2 is **complete, balanced, compliant, and explainable**—and generate human‑readable reports (and machine‑readable attestations) that programs, reviewers, and clients can trust.
**Done means:** all structural checks pass; fairness and minimum‑coverage guarantees are met; policy and licensing constraints are respected; drift vs. prior plans is understood; a signed report and machine certificate exist, both tied to a KOS snapshot/version.

### 2) Inputs & outputs (data contracts)

* **Inputs**

  * Coverage Plan table (from Module 2): `concept_id, source, path_to_root, depth, facets (e.g., locale, modality, difficulty), quota, notes, plan_version, kos_snapshot_id, allocation_method`.
  * Concept tables/graph (from Module 1) for validation: node existence, labels, deprecation flags, mappings.
  * Policy configuration: forbidden branches, jurisdictional filters, minimum per‑branch quotas, licensing rules.
  * Historical baselines (optional): prior Coverage Plans and their reports for drift analysis.
* **Outputs**

  * **Audit dataset**: a denormalized table with all computed indicators per stratum/branch.
  * **Coverage certificate** (machine‑readable JSON/YAML): pass/fail flags, metric values, thresholds, lineage (KOS & Plan versions), signatures.
  * **Human report**: PDF/HTML describing checks, warnings, waivers, and recommended remediations; branch and slice visualizations; changelog/diff since last plan.

*(Store outputs alongside the Coverage Plan under immutable versioned paths; every artifact includes `kos_snapshot_id` and `plan_version`.)*

### 3) Core components

**A) Structural & referential integrity checker**

* Ensures every `concept_id` appears in the authoritative concept table; flags **orphan IDs**, **deprecated/obsolete** nodes, and **cycle symptoms** (e.g., impossible depths).
* Verifies **referential integrity** on parent/child relations reconstructed from `path_to_root`.
* Confirms **unique IDs**, **non‑negative quotas**, and **facet vocabulary** conformance (values belong to the declared domain).

**B) Fairness & balance engine**

* Computes distributional metrics across branches and facets: per‑branch quota share, **entropy**, **Gini coefficient**, **Herfindahl‑Hirschman Index** for concentration.
* Applies policy **floors/ceilings** (e.g., “≥1% for each top‑level branch”; “≤40% for any single branch”), with explicit pass/fail flags.
* Produces **heatmaps** of quota density by facet (e.g., locale×difficulty), highlighting sparse or saturated cells.

**C) Compliance & policy validator**

* **Licensing guardrails:** if a KOS is restricted, verify that exports don’t leak forbidden fields (e.g., blocks full definition text in downstream artifacts).
* **Safety filters:** ensure **forbidden topics** are excluded or quarantined; check that **jurisdictional constraints** are respected (e.g., EU content does not leak into US‑only slices).
* **PII/PHI posture:** confirms the Coverage Plan includes required **redaction flags** where sensitive domains are present and references the correct compliance frameworks in metadata.

**D) Drift & delta analyzer**

* Compares current vs. previous Coverage Plan: added/removed concepts, **quota deltas** per branch, **method changes** (e.g., proportional → Neyman), and **impact on fairness metrics**.
* Explains drivers: overlay additions from Module 4, policy changes, or cost adjustments.

**E) Quality gates & statuses**

* *Blocking* (must pass): structure, referential integrity, non‑negative quotas, forbidden concepts absent, deprecations handled, minimum per‑branch floors.
* *Advisory* (warn): high concentration, large drift without rationale, sparse high‑risk slices, excessive zero‑quota leaves under active branches.
* Each gate has a **threshold** and **owner** (who can formally waive it), producing a **green/yellow/red** badge per section.

**F) Report generator**

* **Executive summary**: one page with green/yellow/red and top actions.
* **Methodology**: allocation method, fairness constraints, and KOS snapshot details.
* **Findings**: tables/visuals per branch/facet; lists of quarantined or deprecated concepts; policy notes and waivers.
* **Appendices**: full indicator tables; machine‑readable certificate; diff vs. prior plan.

### 4) Operational concerns

**Performance & scale**

* Operate on **columnar** Coverage and concept tables (Parquet) with `DuckDB` for fast group‑bys and joins.
* Precompute **branch sizes**, **depths**, and **leaf flags** in Module 1 to avoid graph traversals here.

**Observability & lineage**

* Every check emits structured logs with **metric name, value, threshold, status, context**.
* Attach **OpenTelemetry** spans for long‑running aggregations.
* All outputs embed `kos_snapshot_id`, `plan_version`, timestamps, and the **policy pack** commit hash.

**Governance**

* A **sign‑off workflow** captures who approved the plan, on what date, with which waivers.
* **Immutable archives** of reports and certificates support later audits and reproducibility requirements.

**Security & licensing**

* Respect per‑KOS ACLs in all exports; if a KOS forbids redistributing labels/definitions, the auditor uses **hashed content** in internal logs and surfaces only **counts/IDs** in reports.

**Python libraries to rely on**

* Data: `pandas`, `pyarrow`, `duckdb`.
* Validation: `pandera` (tabular checks), `pyshacl` (graph shape validation when needed).
* Metrics & viz: `numpy`, `scipy` (for indices), `matplotlib`/`plotly`/`altair` for charts (report export handled by `weasyprint`/`reportlab` if PDF needed).
* Packaging & signing: `hashlib` and a simple PKI wrapper for certificate signing.

---

## Module 6 — **Eval Blueprint Generator (Slices & Metrics)**

*(turn the Coverage Plan into a formal, versioned “Evals‑as‑PRD” suite, with deterministic graders, slice definitions, and reporting contracts)*

### 1) Mission & “definition of done”

**Mission:** transform the Coverage Plan into a **formal evaluation specification**—suites, slices, item schemas, graders, metrics, acceptance thresholds, and run‑time parameters—so model quality can be assessed consistently across versions and vendors.
**Done means:** there is a **versioned eval suite** that can be executed repeatedly across models, with **deterministic graders** (or well‑specified LLM‑judging protocols), **stable seeds**, and **auditable slice coverage** tied to concept IDs.

### 2) Inputs & outputs (data contracts)

* **Inputs**

  * Coverage Plan (Module 2): concept IDs, facets, quotas, difficulty bands.
  * Instruction Pack & rubric (project docs): criteria, rating scales, disqualifiers, examples.
  * Policy pack: behavior specs, refusal criteria, safety requirements.
  * Optional: seed datasets (pilot items), historical eval results for baselining.
* **Outputs**

  * **Eval suite manifest** (machine‑readable): suite ID, version, slice definitions, sampling logic, metric definitions, acceptance thresholds, model adapters, random seeds, allowed tool use.
  * **Item schemas** per task type (classification, extraction, generation, pairwise preference, code/agent tasks), with metadata binding to Coverage concept IDs and facets.
  * **Grader specifications**: deterministic checkers, rubric scorers, or LLM‑as‑judge protocols (prompts, temperature, references, calibration settings).
  * **Runner configuration**: concurrency, retries, caching, rate limits, sandbox policies.
  * **Documentation pack**: human‑readable PRD explaining scenarios, slices, and how to interpret metrics.

*(All artifacts are versioned; manifests pin hashes of item sets and code for graders.)*

### 3) Suite composition & slicing strategy

**A) Suite scaffolding**

* Organize by **scenario** (e.g., “M&A issue spotting”, “Prospectus gap detection”), each with a **test type** (classification/extraction/generation/pairwise/agentic).
* Define **slices** that map directly to Coverage Plan strata: by branch, depth band, locale, difficulty, and any policy tags (e.g., safety‑critical).
* Allocate **item counts** per slice respecting quotas, with optional **pairwise design** for preference tasks (balanced sampling of positive/negative pairs).

**B) Item provenance & stability**

* For static suites, commit **immutable item files** (inputs + expected outputs/keys).
* For semi‑dynamic suites (sampled from a larger pool), fix **random seeds**, sampling frames, and **inclusion/exclusion lists** per version to ensure near‑identical slice composition across runs.

**C) Cross‑suite consistency**

* Keep a **global registry** of slices and metrics so a “EU competition hard” slice means the same thing across suites and releases.
* Enforce **no concept leakage** between train/dev/test if the same concept space feeds both data creation and evals.

### 4) Item types & grader contracts

**A) Deterministic graders (preferred where possible)**

* **Classification / tagging**: exact label match or label‑set match; normalization rules documented (case, whitespace, punctuation).
* **Extraction / structured output**: JSON Schema or Pydantic model validation; field‑level scoring; tolerance windows for numerics/dates; synonym dictionaries attached to the grader.
* **String similarity**: token‑level F1, EM; use domain‑appropriate metrics sparingly (BLEU/ROUGE for summarization only when justified).
* **Code/math**: unit tests, doctests, symbolic solvers, or execution‑based verdicts in a **sandbox** (resource/time limits, no network).

**B) Preference & alignment tasks**

* **Pairwise preference**: present (A,B) and require a ranking; aggregate with **Bradley–Terry** or **Thurstone** models; report **win‑rates by slice**.
* **DPO‑ready pairs**: ensure balanced, high‑quality pairs with metadata preserved for downstream training use.

**C) Rubric‑based human scoring**

* Where subjectivity is unavoidable, encode rubric criteria (e.g., accuracy, completeness, legal sufficiency) with **scale anchors** and **adjudication rules**; compute **inter‑rater agreement** (κ/α) as a first‑class metric and block publication if below threshold.

**D) LLM‑as‑judge (only with guardrails)**

* Strict **protocols**: fixed prompts, zero or low temperature, **reference materials provided**, **verbatim quote requirement** for justifications, and **content‑hiding** (judge cannot see model identity).
* **Calibration set**: a small, human‑gold set to **calibrate and monitor** the judge (check false‑positive/negative rates and bias).
* **Adversarial checks**: probe the judge for anchor/context bias; rotate order of candidates for pairwise judgments.
* **Transparency**: include judge model/version, prompts, and a **hash** of the evaluation template in the manifest.

### 5) Metric framework & acceptance criteria

**Core metrics (pick per task type)**

* **Accuracy / EM / token‑F1** for classification and extraction.
* **Pass@k / success@k** for code/agents; **latency** and **tool‑use success** for agent tasks.
* **Preference win‑rate** and **BT log‑likelihood** for pairwise tasks.
* **Rubric average**, **IAA** (κ/α) for human‑scored tasks.
* **Refusal rate**, **policy violation rate**, **hallucination rate** for safety/behavior slices.

**Statistical treatment**

* **Confidence intervals** via nonparametric bootstrap at the slice and suite levels.
* **Significance testing** for regressions/improvements with multiple‑comparison correction across slices.
* **Effect sizes** (e.g., Cohen’s h for proportions) to communicate practical impact.

**Acceptance gates**

* Per‑slice thresholds (e.g., ≥0.85 F1 on “EU competition hard”).
* Suite‑level composite thresholds (weighted across critical slices).
* **Safety blocks**: any policy‑violation slice above threshold fails the suite, regardless of task metrics.

### 6) Runner & execution architecture

**Adapters to model providers**

* A clean abstraction for model calls (prompt, parameters, tool permissions), with **per‑provider back‑pressure** (rate limits, retries, exponential backoff), **caching**, and **determinism controls** (seeds, temperature caps).

**Sandbox & tool use**

* For code/agent tasks, an **isolated execution environment** with strict resource/time/network controls; ephemeral containers, read‑only file systems, and recorded I/O for replay.

**Caching & reproducibility**

* Query/result cache keyed by **(model_id, prompt_hash, params)** to keep costs manageable and results repeatable across runs.
* Explicit **random seed** fields in the manifest for any sampling or stochastic graders.

**Telemetry & logging**

* Per‑item logs: inputs, outputs, grader verdicts, scores, confidences, time, cost, and any judge rationales.
* Aggregation logs: slice roll‑ups, CI calculations, failures.
* OpenTelemetry spans for end‑to‑end timing; cost accounting per suite and per slice.

### 7) Reporting & deliverables

**Scorecards**

* **Slice leaderboard**: core metrics per slice, CI bands, deltas vs. baseline; traffic‑light badges.
* **Failure analysis**: example clusters (by error code), confusion matrices, typical error patterns per branch.
* **Safety & behavior**: refusal/violation rates by policy slice, with concrete exemplars and anonymized snippets.
* **Comparative plots**: model‑to‑model or version‑to‑version comparisons with significance annotations.

**Artifacts**

* Machine‑readable **results bundle** (scores + per‑item logs + config manifest).
* Human‑readable **Eval PRD** appendix describing how items were sampled, graded, and aggregated; limitations and caveats.

### 8) Governance, trust, and ethics

**Versioning & freezing**

* Pin **suite version**, **item hashes**, **grader code hash**, **judge model/version**, and **random seeds**; no change without a version bump.
* Maintain a **deprecation policy** for bad items (e.g., leaked private info, errors); document replacements and impact.

**Bias & safety**

* Include **fairness slices** by sensitive facet where appropriate (and lawful).
* Red‑team slices explicitly designed to probe policy boundaries; document outcomes and remediation.

**Separation of concerns**

* Clear boundary between **eval construction** and **model teams** to avoid overfitting; if a client requires, run blind (model identities blinded in reports).

**Access & licensing**

* Respect KOS licensing in any displayed labels/definitions inside reports; redact as needed; include license notices in the PRD.

**Python libraries to rely on**

* Data & orchestration: `pandas`, `pyarrow`, `duckdb`, `typer`/`click` for CLI.
* Metrics: `scikit‑learn`, `numpy`, `scipy`, `statsmodels` (CIs/tests), `sacrebleu`, `rouge‑score` (only when appropriate).
* Human‑score aggregation & IAA: `scikit‑learn` (κ), `krippendorff`.
* Judge protocols & structured outputs: `jsonschema`, `pydantic`, structured‑output frameworks (Guardrails/outlines‑style).
* Sandboxing: container runtime of your choice with Python wrappers; resource control via OS‑level quotas.
* Optional harnesses: adapters to **OpenAI Evals**, **HELM‑style** runners, and **EleutherAI lm‑evaluation‑harness** where applicable.

---

## How Modules 5 & 6 work together (and with 1–4)

1. **Module 2** hands Module 5 a Coverage Plan; Module 5 certifies that the plan is structurally sound, balanced, and compliant, producing a **coverage certificate**.
2. **Module 6** consumes the certified plan + rubric to generate a **versioned eval suite** whose slices mirror the plan; graders are pinned and reproducible.
3. When **Module 4** publishes overlay expansions (new subtopics), Module 5 re‑audits the plan (new certificate), and Module 6 releases **suite v+1** with corresponding slices.
4. **Module 3** benefits indirectly: clearer coverage and new overlay nodes reduce mapping ambiguity, which you’ll see reflected as **cleaner error taxonomies** in Module 6 reports.

The result is a closed loop: **plan → certify → evaluate → learn → refine**—with each step leaving behind auditable, versioned artifacts that laboratories and compliance teams can verify.

Absolutely—here’s a **purely narrative, implementation‑level architecture** for the remaining pieces: **Module 7 (Governance, Versioning & Diffs)**, the **CLI & service layer**, the **LLM Prompt Pack**, and the small set of **supporting components** that make the whole system auditable, reproducible, and enterprise‑ready. No code or pseudocode—only structure, responsibilities, data contracts, and operational detail. I’ll call out the Python libraries you’d likely use.

---

## Module 7 — **Governance, Versioning & Diffs**

**Mission:** make every artifact in the pipeline traceable, reproducible, and reviewable; prevent silent regressions; and enable safe rollbacks. This module establishes the “source‑of‑truth registry” and the rules for change.

### 1) Objects under governance (the registry’s scope)

Treat each as a first‑class, versioned asset with lineage:

1. **KOS snapshots** (from Module 1): raw sources, normalized graph, flattened tables, search/vector indexes, license metadata.
2. **Coverage Plans** (Module 2): the plan table, allocation method/parameters, policy pack, fairness thresholds, audit certificate (Module 5).
3. **Mappings & crosswalks** (Module 3): mapping records, candidate logs, proposed cross‑scheme links, adjudication decisions.
4. **Overlay scheme** (Module 4): proposed/approved extension nodes, synonyms, deprecations, change log.
5. **Eval suites** (Module 6): manifests, item sets or sampling frames, grader specs, judge protocols, acceptance thresholds.
6. **Prompt Pack** (below): prompt templates, structured‑output schemas, retrieval policies, red‑team suites.
7. **Run bundles**: per‑run configs, per‑slice results, grader verdicts, judge outputs, telemetry, cost ledger.
8. **Certificates & reports**: coverage certificates, evaluation scorecards, signed release notes.

Each object has: a unique ID, semantic version, cryptographic hash of content, creator, timestamp, parent(s), and references to upstream objects (e.g., Coverage Plan → KOS snapshot ID).

### 2) Versioning policy

* **Semantic versioning** across all artifacts:

  * **Major**: breaking structure changes or policy shifts (e.g., adding a new facet or metric that affects comparability).
  * **Minor**: additive but compatible changes (e.g., adding slices, expanding overlay).
  * **Patch**: corrections with no intended behavioral change (typo fix, label correction).
* **Content hashing**: compute a normalized hash for every artifact; the registry stores both the declared semantic version and the computed hash.
* **Linkage rules**: each published artifact pins upstream versions by ID and hash. A Coverage Plan must pin a KOS snapshot; an Eval Suite must pin both a Coverage Plan and the graders.

### 3) Metadata model (what the registry records)

For every artifact: type, version, hash, human title/summary, upstream links, policy pack hash, license tag, change reason code, reviewer(s), approvals, and (if applicable) waiver IDs. Include environment fingerprints for anything executable (library versions, OS, container image digests).

### 4) Release lifecycle

* **Propose → Build → Audit → Approve → Sign → Publish**

  * *Propose*: open a change request with rationale (coverage gap, cost, risk).
  * *Build*: produce candidate artifact and attach upstream pins.
  * *Audit*: run defined checks (Module 5 for Coverage; self‑checks for others).
  * *Approve*: named approvers sign off (domain lead, QA, legal if needed).
  * *Sign*: cryptographically sign artifact manifests.
  * *Publish*: push to the registry and mark “current” for the program.

Use a small change‑control board for Major changes; Minor/Patch can follow a lightweight two‑person rule.

### 5) Diffing strategy (per artifact type)

* **KOS snapshots:** report added/removed/renamed concepts, mapping churn, branch size deltas, new deprecations, and license changes.
* **Coverage Plans:** added/removed strata, quota deltas by branch/facet, fairness metric deltas (entropy, Gini), and allocation‑method changes.
* **Mappings:** added/removed/overridden decisions; churn by branch; ambiguity‑rate changes; precision/recall vs. gold set (if any).
* **Overlay scheme:** newly approved nodes, merges/splits, synonyms added, deprecations; net coverage gain measured against observed corpora.
* **Eval suites:** slice composition changes, item hash churn, grader/judge protocol changes, threshold shifts.
* **Prompt Pack:** template or schema changes, retrieval policy updates, judge prompts touched.
* **Run bundles:** model‑to‑model score diffs with CI bands, per‑slice significance markers, cost/latency deltas.

Diffs must be human‑readable (for approvers) and machine‑readable (for audit automation).

### 6) Policy, waivers, and risk acceptance

* **Blocking gates** (cannot publish if failing): referential integrity, licensing compliance, forbidden‑topic exclusions, baseline fairness floors, grader reproducibility.
* **Advisory gates** (publish with waiver): large drift, low annotator agreement in pilots, slice sparsity.
* **Waiver records** capture the justification, owner, expiration date, and planned mitigation.

### 7) Rollbacks & disaster recovery

* **Atomic rollbacks**: every “current” pointer can revert to the last green artifact; downstream artifacts warn if their upstream pointer is rolled back.
* **Replay recipes**: each published run bundle can be re‑executed given the pinned artifacts; store container image digests and environment manifests.
* **Backups**: replicate the registry and object store across regions; regularly test restore of large artifacts (e.g., item sets) and indexes.

### 8) Observability & audit

* **Lineage graph**: interactive view of artifact dependencies; click through to see diffs and signatures.
* **Event log**: append‑only, signed events for proposals, approvals, waivers, publishes, rollbacks.
* **Telemetry**: SLIs/SLOs for publication lead time, audit failure rate, rollback frequency, registry latency.

### 9) Access, tenancy, and licensing

* **RBAC**: creators, reviewers, approvers, auditors, and readers; separate roles for overlay editing vs. KOS ingestion.
* **Tenancy**: hard separation of client namespaces; artifact cross‑links forbidden unless explicitly shared.
* **Licenses**: per‑artifact license tags with enforcement policies (e.g., mask restricted labels in public reports).

**Useful Python stack (governance layer):** DVC or LakeFS (data versioning), Git/GitPython (metadata repos), `deepdiff`/`pandas` for tabular diffs, `networkx` for lineage graphs, `hashlib` and a signing tool (Sigstore or GPG bindings), `pydantic` for manifest schemas, `rich`/`textual` for human diffs in terminal.

---

## CLI & Service Layer

**Mission:** give operators and SPLs a safe, consistent interface to run every step locally or in CI/CD, and expose a small HTTP API for programmatic control.

### 1) Command‑line design (human‑first)

* **Verbs & nouns** mirror the modules: ingest, snapshot, plan, audit, map, expand, certify, evalgen, publish, diff, rollback, run, report.
* **Idempotency**: repeated invocations with the same inputs produce identical artifacts; “dry‑run” flags show what would change.
* **Configuration precedence**: command flags override environment variables, which override project config files; all resolved config is printed for traceability.
* **Context management**: named contexts (dev, staging, prod; or client A/B) controlling registry endpoints, credentials, and data roots.
* **Progress & logging**: structured logs to file; concise progress to TTY; optional verbose and JSON logs for CI.

### 2) Safety rails

* **Preflight checks** before any publish (license flags, forbidden topics, integrity checks).
* **Confirmations** for destructive operations (un‑publishing, rollbacks).
* **Resource controls**: max batch size per command, default timeouts, rate‑limit awareness for remote endpoints.
* **Secrets**: no secrets on the command line; everything via environment or secrets manager.

### 3) Extensibility

* **Plugin hooks**: new KOS loaders, mappers, graders, and report renderers register by entry‑point name; the CLI discovers them at startup.
* **Profiles**: saved command bundles (e.g., “legal‑pilot‑baseline”) that execute a sequence with pinned versions and thresholds.

### 4) Service/API layer (automation‑first)

* **FastAPI** service with endpoints for artifact CRUD in the registry, job submission for long‑running tasks (plan build, eval run), and artifact downloads.
* **AuthN/Z**: JWT or mTLS; per‑endpoint RBAC aligned to registry roles; audit headers (who, when, why).
* **Jobs & queues**: asynchronous job execution with status polling, retries, and logs; tags for tenant/project to enable back‑pressure controls.
* **Rate limits & quotas**: per‑tenant compute and cost guardrails; early rejection with informative errors.
* **Health & readiness**: health endpoints, dependency checks, slow‑query warnings.

**Useful Python stack (CLI/API):** Typer or Click (CLI), Rich (TTY UX), FastAPI + Uvicorn (HTTP), SQLModel or Pydantic for request/response schemas, Celery/RQ or Prefect for job orchestration, OpenTelemetry for traces.

---

## LLM Prompt Pack (Templates, Protocols, and Guardrails)

**Mission:** centralize, version, and test all prompts and protocols used by the system so they are consistent, auditable, and safe.

### 1) What the Prompt Pack contains

* **Template library** organized by task: mapping disambiguation, crosswalk justification, overlay proposal, self‑critique, difficulty banding, judge protocols, red‑team probes.
* **Output schemas**: JSON Schemas for each template with required fields, value ranges, and enumerations.
* **Retrieval policies**: what evidence is allowed (ontology definitions, sibling labels, corpus snippets), maximum token budgets per source, privacy filters.
* **Model routing**: preferred model families per template, fallback order, and per‑provider parameter constraints (temperature ceilings, max output tokens).
* **Evaluation assets**: calibration sets for judge templates, yardsticks for constraint adherence, and historical acceptance rates for proposal templates.

### 2) Design principles

* **Grounding**: every decision‑making template includes the authoritative definitions or policy text it must cite; the prompt explicitly forbids using external knowledge.
* **Constrained outputs**: all generation tasks must return structured outputs validated against the schema; reject anything that fails validation.
* **Citations**: proposal and judgment templates require quoting spans from the evidence and indicate their source.
* **Role separation**: generation, critique, and approval are separate templates to prevent self‑justification bias.
* **Determinism**: low or zero temperature for adjudication; fixed seed contexts; order‑randomization for pairwise judgments to avoid position bias.

### 3) Governance & versioning for prompts

* **Semantic versions** and change logs explain why a template changed (e.g., reduced hallucination rate, better adherence).
* **A/B testing**: new versions are flighted on a subset and compared for constraint adherence, acceptance rate, and downstream quality.
* **Compatibility**: prompt versions are pinned inside artifact manifests (e.g., which mapping template version was used to produce a crosswalk).

### 4) Quality metrics

* **Constraint adherence**: percent of responses that validate against the schema on first pass.
* **Grounding fidelity**: percent of claims with correct citations to provided evidence.
* **Hallucination rate**: incidence of IDs or facts not in the evidence pack.
* **Human acceptance**: reviewer approval rate for proposals and adjudications.
* **Cost & latency**: median tokens and wall‑clock times per template.

**Useful Python stack (around prompts):** jsonschema or Pydantic for validation, a structured‑output framework to enforce grammars, token counters for budgeting, a small metrics store to track per‑template performance over time.

---

## Supporting Components (the rest of the “glue”)

### A) Reviewer Workbench (HITL)

* **Purpose:** adjudicate mappings, approve overlay proposals, review eval item failures.
* **Views:** side‑by‑side evidence; lineage of decisions; sibling/parent context; similarity clusters of near‑duplicates; one‑click accept/override with reason codes.
* **Ergonomics:** keyboard‑first review, bulk actions for repetitive cases, conflict detection.
* **Data flow:** writes go to the registry as new decisions; every action carries reviewer ID and timestamp.

### B) Telemetry, Cost, and Capacity

* **Metrics:** per‑module throughput, error rates, rework rates, LLM cost per artifact, annotator time estimates by stratum.
* **Dashboards:** capacity planning (who/what/when), budget burn‑down, and alerting for anomalies (e.g., sudden spike in judge failures).
* **Chargeback:** attribute cloud and model API spend to tenants/projects; show cost per accepted item and per eval suite.

### C) Storage/Layout & Lifecycles

* **Object store layout:** top‑level namespaces by tenant → project → artifact type → version; all content‑addressed.
* **Cold storage & TTLs:** raw corpora and heavy item sets move to cold storage after retention window; manifests always hot.
* **PII handling:** tag PII‑bearing artifacts; enforce encryption at rest, access logs, and deletion workflows.

### D) Security & Compliance

* **RBAC & least privilege:** separate roles for ingest, overlay editing, mapping adjudication, and publishing.
* **Secrets:** centralized secrets manager and per‑context allowlists for model endpoints.
* **Data residency:** context configs enforce storage region and model‑endpoint residency (e.g., EU‑only).
* **Audit trails:** append‑only logs and periodic attestations bundled with releases.

### E) Rollout & Maturity Roadmap

* **Phase 1 (pilot)**: Module 1–3 with minimal governance; single‑tenant; manual approvals.
* **Phase 2 (scale)**: add Module 5–6; Prompt Pack v1; registry with semantic versions; basic RBAC.
* **Phase 3 (enterprise)**: Module 7 fully enforced; A/B prompt testing; waiver workflows; signed certificates; multi‑tenant isolation; disaster‑recovery drills.

---
---

## 16) Dedicated GPU build

* **One compiled engine**: Qwen3‑32B, **W4A8 (AWQ)**, **paged KV**, **FP8 context FMHA enabled** (supported in recent TRT‑LLM releases). ([NVIDIA GitHub][2])
* **One serving endpoint**: **Triton Inference Server** with the **TensorRT‑LLM backend**, configured for **in‑flight batching**, **paged KV cache**, and **guided decoding** (XGrammar) for strict JSON outputs. ([GitHub][3])
* **Optional speedups**: **Speculative/recurrent drafting** for long generations (enabled later if needed). ([NVIDIA Developer][4])

---

## 1) Environment & prerequisites (pin versions through containers)

**Why containers:** They eliminate host/driver/CUDA mismatches. We use two NVIDIA NGC images: one to **build** engines (TRT‑LLM “release”/“devel”), and one to **serve** (Triton with the TRT‑LLM backend). Confirm aligned versions via **TRT‑LLM release notes** + **Triton release notes** and the backend support matrix. ([NVIDIA GitHub][2])

1. **GPU/driver**: You have **RTX 5090 (Blackwell, 32 GB GDDR7)**. Keep your NVIDIA driver current enough for the container tag you pick; the container’s CUDA/TensorRT stack will dominate. ([NVIDIA][5])
2. **Docker + NVIDIA Container Toolkit**: Standard setup for GPU access inside containers.
3. **NGC containers to pull**

   * **Build**: `nvcr.io/nvidia/tensorrt-llm/release` (or the **devel** image if you need the full toolchain; both are published in NGC). ([NVIDIA NGC][6])
   * **Serve**: `nvcr.io/nvidia/tritonserver:<xx.yy>-trtllm-python-py3` (the “trtllm‑python” tag bundles the **TensorRT‑LLM backend**). Pick `<xx.yy>` to match your TRT‑LLM version per the backend’s **support matrix**. ([NVIDIA NGC][7])
4. **Documentation anchors you will follow** (pin these in your runbook)

   * **TRT‑LLM Quick Start & Support Matrix** (model support, features, commands). ([NVIDIA GitHub][8])
   * **TRT‑LLM Release Notes** (ensure **Qwen3** support; confirm FP8 context FMHA with W4A8 workflow). ([NVIDIA GitHub][2])
   * **Triton TRT‑LLM backend** docs (in‑flight batching, paged attention/KV, guided decoding, speculative modes). ([NVIDIA Docs][9])

---

## 2) Get the model (Qwen3‑32B) and freeze a snapshot

* **Source**: Official **Qwen/Qwen3‑32B** on Hugging Face (model card/README). Accept license if required and record the **commit hash** in your build manifest. ([Hugging Face][1])
* **Evidence of ecosystem availability**: You’ll see Qwen3‑32B variants across HF, GGUF conversions, and third‑party hosting—use **only** the official base for engine builds. ([Hugging Face][10])
* **Snapshot discipline**: Save the tokenizer files and the exact model revision hash—your build manifest must include these so downstream evals can pin the **engine hash** back to this origin.

---

## 3) Engine build (TensorRT‑LLM) — **W4A8 (AWQ) + paged KV**

> Goal: produce a **TensorRT‑LLM engine** for **Qwen3‑32B** with **W4A8**, **paged KV** and **FP8 context FMHA**. This profile is the sweet spot for a single RTX 5090 (32 GB) and aligns with current TRT‑LLM quantization workflows. ([NVIDIA GitHub][2])

### 3.1 Quantization options you will consider

* **W4A8 (AWQ)** = **INT4 weights + 8‑bit activations**. Recommended default for 32B on a single 32 GB card. Recent TRT‑LLM releases also mention **FP8 context FMHA support for the W4A8 workflow**, which increases prefill efficiency. ([NVIDIA GitHub][2])
* **FP8** (weights/activations) is supported, but for 32B on 32 GB VRAM once you add KV cache and batching, headroom is limited. Reserve FP8 for A/B tests.
* **Hardware note**: FP8/W4A8 quant flows require **Ada/Hopper/Blackwell‑class** Tensor Cores (your 5090 qualifies). ([NVIDIA Docs][11])

### 3.2 Conversion & build workflow (repeatable, containerized)

1. **Launch the TRT‑LLM build container** (`…/tensorrt-llm/release`). Follow the **Quick Start Guide** to mount your model directory and a workspace for outputs. ([NVIDIA GitHub][12])
2. **Convert HF checkpoint → TRT‑LLM checkpoint** using the Qwen/Qwen3 example path indicated in **TRT‑LLM release notes** (“see `examples/models/core/qwen`”). This step normalizes weights/tokenizer and sets up the mapping. ([NVIDIA GitHub][2])
3. **Apply quantization**

   * For **W4A8**: Use the TRT‑LLM quantization pipeline (AWQ). TRT‑LLM’s quantization blog and docs call out **W4A8** as a first‑class option; ensure your calibration set and per‑layer scales are generated. ([NVIDIA GitHub][13])
4. **Build the engine** with **trtllm‑build** using these principles:

   * **Paged context attention** **ON** (enables **KV‑cache reuse** and **chunked context** later): `--use_paged_context_fmha enable`. ([NVIDIA GitHub][14])
   * **KV cache type**: build for **paged** cache; set the **KV quant** you intend to use at runtime (FP8 recommended on Blackwell). TRT‑LLM exposes **`--kv_cache_type`** in the build tool; set it to **paged**. ([NVIDIA GitHub][14])
   * **FP8 context FMHA**: keep **enabled**; it’s on by default when FP8 is used, and is supported in the W4A8 workflow per release notes. ([NVIDIA GitHub][14])
   * **Tokens per block**: the default **32** is fine; smaller blocks waste memory, larger blocks may reduce reuse. Leave default unless profiling dictates otherwise. ([NVIDIA GitHub][14])
   * **Max tokens / batch**: size these to your expected concurrency and context lengths. Remember: KV cache is the real VRAM consumer at runtime.
5. **Record the build manifest**

   * Include: upstream HF commit hash, tokenizer hash, quantization method (**W4A8**), build flags (`--use_paged_context_fmha`, `--kv_cache_type paged`, tokens per block, max tokens), and the final **engine hash**. This manifest becomes the artifact pinned by the rest of your system.

> References: **trtllm‑build** flags for paged context/FMHA and KV cache; KV reuse requires paged context attention. ([NVIDIA GitHub][14])

---

## 4) Serving (Triton + TensorRT‑LLM backend)

We will serve the engine with **Triton Inference Server** using the **TensorRT‑LLM backend**. The backend gives you **in‑flight batching**, **paged KV attention**, **guided decoding (XGrammar)**, and **speculative decoding** modes under one HTTP/gRPC surface. ([GitHub][3])

### 4.1 Pick the correct container tag

Use the NGC image `nvcr.io/nvidia/tritonserver:<xx.yy>-trtllm-python-py3`. The “trtllm‑python” variant bundles the TRT‑LLM backend. Make sure `<xx.yy>` matches your TRT‑LLM release (see release notes and backend repo for aligned versions). ([NVIDIA NGC][7])

### 4.2 Model repository layout & required knobs

The TRT‑LLM backend repo provides a **reference model repository** under `all_models/inflight_batcher_llm/…`. Use that structure and copy your engine into the right subfolder (`tensorrt_llm/1/`). The same reference shows how to launch Triton with the backend and update configs. ([GitHub][3])

**Key configuration (config.pbtxt) to set for Qwen3‑32B:**

* **Batching / scheduling**

  * `batching_strategy: inflight_fused_batching` (turns on **in‑flight batching**) and set small **`triton_max_batch_size`** (e.g., 4–8) plus **`max_queue_delay_microseconds`** ~1–3 ms for interactive workloads. ([NVIDIA Docs][15])
* **KV cache & reuse**

  * Build already set **paged context**; at serving, enable **KV reuse** (saves prefill cost when prefixes repeat).
  * In config, set parameter `enable_kv_cache_reuse: "true"` (see KV‑reuse doc). ([NVIDIA GitHub][16])
  * Consider `enable_chunked_context: true` in config for long inputs (requires the build options you used). ([NVIDIA Docs][17])
* **Guided decoding (strict JSON/EBNF)**

  * `guided_decoding_backend: xgrammar`.
  * Python backend needs `tokenizer_dir`; **C++ backend** requires a **tokenizer info JSON** path: `xgrammar_tokenizer_info_path`. Generate it using NVIDIA’s tool (`generate_xgrammar_tokenizer_info.py`) before starting Triton. These fields are **required** when guided decoding is enabled. ([NVIDIA Docs][18])
  * Use guided decoding whenever your outputs must conform to a **JSON Schema** (our default in mapping/eval tasks). ([NVIDIA Docs][18])
* **Decoding modes**

  * Default to greedy/low‑temperature/top‑p as needed. The backend supports **ReDrafter**, **Lookahead**, **Eagle** for speculative decoding; you’ll enable these only for long generations (see §5). ([NVIDIA Docs][9])

**Health & perf inputs/outputs:** You can request **`return_perf_metrics`** in inputs to get KV‑cache reuse stats and timings back from the backend, which is helpful for your dashboards. ([NVIDIA Docs][17])

---

## 5) Optional: speculative / recurrent drafting (for long answers)

When you encounter long, explanation‑heavy generations (judge rationales, overlay narratives), enable **speculation** for throughput without quality loss:

* Use **ReDrafter** (Apple’s recurrent drafting) or **Lookahead**; both are supported in TRT‑LLM. Start with a short draft length (8–16 tokens) and aim for **acceptance ratio ≥ 0.6**. ([NVIDIA Developer][4])
* Speculative decoding is configured via the **`tensorrt_llm_bls`** model type in Triton (see docs). You reference your main engine as the **target** and a smaller draft engine for pre‑token proposals. Enable it only when you really need long outputs; not required for our default **schema‑bound** short responses. ([NVIDIA Docs][17])

---

## 6) Runtime policies (what we enforce in requests)

* **Low temperature**, fixed sampling parameters for mapping and judge protocols (determinism).
* **Guided JSON** with a **JSON Schema** or EBNF grammar for all structured outputs (mapping results, rubric aggregation, overlay proposal objects). This reduces invalid outputs dramatically because conformance is enforced **at decode time**. ([NVIDIA Docs][18])
* **Tight contexts**: Only pass authoritative definitions/scope notes and sibling labels needed for disambiguation—smaller prefill means more concurrency and less KV pressure.
* **Return perf**: set **`return_perf_metrics: true`** in requests during calibration to capture KV reuse stats and saturation, then turn off in steady state. ([NVIDIA Docs][17])

---

## 7) Observability & SLOs

Log per request: `engine_hash`, `quant_method: W4A8`, `kv_cache: paged+quant(FP8)`, `guided_decoding: on/off`, `tokens_in/out`, `latency_ms`, `queue_delay_us`, `accept_ratio` (if speculative), and **Prompt Template version**. This mirrors the backend’s telemetry capabilities and lets you correlate performance with configuration. ([NVIDIA Docs][17])

---

## 8) Integration contract (how the rest of your Python system calls it)

Expose one internal **LLM provider** with three capability methods; all route to the **same Triton model** (Qwen3‑32B engine), only **guided decoding** and **sampling params** change:

1. **`generate_json(schema, prompt, …)`** → Triton **guided decoding** (`guide_type=“json_schema”`, `guide=<schema>`) with **low temperature**. Default path for mapping, rubric aggregation, overlay objects. ([NVIDIA Docs][18])
2. **`rank_candidates(prompt, candidates)`** → same engine, low temperature; grammar restricts `concept_id` to enumerated choices (closed‑set).
3. **`judge(prompt, reference, …)`** → same engine, low temperature; no guided JSON unless you want structured verdicts; optional **speculative mode** for long rationales.

This keeps Modules 3–6 unchanged when you tweak serving knobs; they never see engine details—only the provider interface.

---

## 9) Capacity planning for a single RTX 5090

* **Qwen3‑32B W4A8 + paged FP8 KV**: Expect **~4k token** contexts with interactive latency and small concurrent batches, especially with **in‑flight batching** and tight prompts. KV cache dominates VRAM consumption; paged, quantized KV is essential for this footprint. ([NVIDIA Docs][9])
* Maintain **20–25% VRAM headroom** to avoid allocator fragmentation and paging thrash; validate with synthetic runs before production. (5090 is **32 GB GDDR7**.) ([NVIDIA][5])

---

## 10) Day‑0 → Day‑2 runbook

**Day‑0 (build & validate)**

* Pull TRT‑LLM “release” container; convert HF → TRT‑LLM checkpoint; quantize to **W4A8**; `trtllm-build` with **`--use_paged_context_fmha enable`** and **`--kv_cache_type paged`**; record the **engine hash**. ([NVIDIA GitHub][14])
* Smoke test with TRT‑LLM quick start clients; confirm outputs match reference answers. ([NVIDIA GitHub][12])

**Day‑1 (serve & calibrate)**

* Start Triton `…-trtllm-python-py3`; place engine in `all_models/inflight_batcher_llm/tensorrt_llm/1/`. Set **in‑flight batching**, **guided decoding** (with **`xgrammar_tokenizer_info_path`**), **KV‑reuse**, and short **queue delay**. ([GitHub][3])
* Run calibration suites: **schema adherence** (should be ~100% with guided JSON), **latency/throughput** at 2–4k token contexts, **KV reuse** metrics, and **judge agreement** vs. human gold.

**Day‑2 (observe & tune)**

* If tail latency spikes: reduce **`max_queue_delay_microseconds`**, verify **paged KV** and reuse are active, and check acceptance ratios if using speculation. ([NVIDIA Docs][9])
* If VRAM pressure: tighten context, reduce output tokens, or pause speculation; FP8 KV is usually the best first lever. ([NVIDIA GitHub][16])

---

## 11) Troubleshooting quick notes

* **Invalid JSON** → Ensure **guided decoding** is actually on (config has `guided_decoding_backend: xgrammar` and the **tokenizer info JSON** path is present). Missing those fields can cause backend errors on startup. ([NVIDIA Docs][18])
* **KV reuse seems ineffective** → Check that you **built** with paged context FMHA and **enabled** reuse in the model config; reuse requires the paged‑context build flag. ([NVIDIA GitHub][16])
* **Throughput not improving with speculation** → Lower draft length or switch method (ReDrafter vs Lookahead); speculation helps most on **long outputs**, not short JSON responses. ([NVIDIA Developer][4])

---

## 12) Canonical references (bookmark these)

* **Qwen3‑32B official (HF / docs / blog)** — confirm model ID, tokenizer, and licensing. ([Hugging Face][1])
* **TRT‑LLM release notes / support matrix / quick start** — confirm **Qwen3** support, **W4A8** workflows, **FP8 context FMHA**, and the **`trtllm-build`** flags. ([NVIDIA GitHub][2])
* **Triton TRT‑LLM backend** — in‑flight batching, KV cache, guided decoding, speculative modes, and **config.pbtxt** parameters (including **XGrammar** and tokenizer requirements). ([GitHub][3])
* **KV‑cache reuse** — enablement in build and serving; why paged context is required. ([NVIDIA GitHub][16])
* **Speculative/recurrent drafting** — ReDrafter overview & integration in TRT‑LLM. ([NVIDIA Developer][4])

---

### Final word

With this design, your entire stack becomes **deterministic, schema‑first, and hardware‑efficient**:

* **One model (Qwen3‑32B)** compiled **once** to a **W4A8** TRT‑LLM engine with **paged FP8 KV**;
* **One server (Triton + TRT‑LLM backend)** exposing **guided JSON** and **in‑flight batching**;
* **One provider interface** in your Python codebase, routing all Module 3–6 calls to this server with the right constraints.

This yields fast, stable, and **audit‑ready** behavior for your mapping, overlay, and judge workflows on a single **RTX 5090**.

[1]: https://huggingface.co/Qwen/Qwen3-32B/blob/main/README.md?utm_source=chatgpt.com "README.md · Qwen/Qwen3-32B at main"
[2]: https://nvidia.github.io/TensorRT-LLM/release-notes.html?utm_source=chatgpt.com "Release Notes — TensorRT-LLM - GitHub Pages"
[3]: https://github.com/triton-inference-server/tensorrtllm_backend?utm_source=chatgpt.com "The Triton TensorRT-LLM Backend"
[4]: https://developer.nvidia.com/blog/nvidia-tensorrt-llm-now-supports-recurrent-drafting-for-optimizing-llm-inference/?utm_source=chatgpt.com "NVIDIA TensorRT-LLM Now Supports Recurrent Drafting ..."
[5]: https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/?utm_source=chatgpt.com "GeForce RTX 5090 Graphics Cards"
[6]: https://catalog.ngc.nvidia.com/orgs/nvidia/teams/tensorrt-llm/containers/release?utm_source=chatgpt.com "TensorRT-LLM Release - NGC Catalog - NVIDIA"
[7]: https://catalog.ngc.nvidia.com/orgs/nvidia/containers/tritonserver?utm_source=chatgpt.com "Triton Inference Server container - NGC Catalog - NVIDIA"
[8]: https://nvidia.github.io/TensorRT-LLM/?utm_source=chatgpt.com "Welcome to TensorRT LLM's Documentation! - GitHub Pages"
[9]: https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/tensorrtllm_backend/README.html?utm_source=chatgpt.com "TensorRT-LLM Backend — NVIDIA Triton Inference Server"
[10]: https://huggingface.co/bartowski/Qwen_Qwen3-32B-GGUF?utm_source=chatgpt.com "bartowski/Qwen_Qwen3-32B-GGUF"
[11]: https://docs.nvidia.com/deeplearning/tensorrt-cloud/v0.3.0-ea/user/build-trt-llm-engine.html?utm_source=chatgpt.com "Building a TensorRT-LLM Engine"
[12]: https://nvidia.github.io/TensorRT-LLM/quick-start-guide.html?utm_source=chatgpt.com "Quick Start Guide — TensorRT-LLM - GitHub Pages"
[13]: https://nvidia.github.io/TensorRT-LLM/blogs/quantization-in-TRT-LLM.html?utm_source=chatgpt.com "Speed up inference with SOTA quantization techniques in ..."
[14]: https://nvidia.github.io/TensorRT-LLM/commands/trtllm-build.html?utm_source=chatgpt.com "trtllm-build — TensorRT-LLM - GitHub Pages"
[15]: https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/tensorrtllm_backend/docs/model_config.html?utm_source=chatgpt.com "Model Configuration — NVIDIA Triton Inference Server"
[16]: https://nvidia.github.io/TensorRT-LLM/advanced/kv-cache-reuse.html?utm_source=chatgpt.com "KV cache reuse — TensorRT-LLM - GitHub Pages"
[17]: https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/tensorrtllm_backend/docs/model_config.html "Model Configuration — NVIDIA Triton Inference Server"
[18]: https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/tensorrtllm_backend/docs/guided_decoding.html?utm_source=chatgpt.com "End-to-End Workflow for Guided Decoding with TensorRT- ..."
