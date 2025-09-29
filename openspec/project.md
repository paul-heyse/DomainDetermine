# Project Context

## Purpose

Build a reusable, standards‑first toolkit that converts a high‑level objective (e.g., “improve legal reasoning on M&A questions”) into **concrete, auditable topic sets** and **evaluation blueprints**. The system ingests authoritative knowledge organization systems (KOS: taxonomies, thesauri, ontologies), plans **coverage** with quotas, maps messy inputs to **stable concept IDs**, extends coverage safely through a curated **overlay**, audits and certifies plans, and generates **eval suites** (“evals as PRD”). Everything is versioned, diffable, and reproducible so AI labs and internal stakeholders can trust the data and evaluations.

Primary outcomes:

* **Coverage Plan**: concept IDs × facets × quotas tied to a frozen KOS snapshot.
* **Mapping & Crosswalks**: free‑text → IDs with evidence and confidence.
* **Overlay Scheme**: reviewer‑approved new subtopics (separate namespace).
* **Coverage Certificate**: pass/fail gates, fairness metrics, and waivers.
* **Eval Suite**: slices, items/frames, grader specs, thresholds, runner configs.
* **Run Bundles**: signed per‑run results for reproducibility and audit.

Non‑goals: model training, proprietary labeling UIs, retaining client data beyond contractual retention, bypassing licensing or data‑residency requirements.

---

## Tech Stack

* **Language & runtime**: Python ≥ 3.11, Linux containers.
* **Data & storage**: Parquet/Arrow, DuckDB (in‑process analytics), object storage for large artifacts.
* **KOS & semantics**: rdflib (RDF/SKOS/SPARQL), owlready2 (OWL 2), pronto/obonet (OBO).
* **Search & similarity**: rapidfuzz (lexical), sentence‑transformers (embeddings), faiss/hnswlib (ANN).
* **Planning & QA**: numpy/pandas, allpairspy (pairwise testing), OR‑Tools/PuLP (allocation under constraints), pandera (tabular QA), pySHACL (graph shape validation).
* **APIs & CLI**: FastAPI (service), Typer/Click (CLI), httpx/tenacity (HTTP client with backoff).
* **Telemetry & quality**: OpenTelemetry (traces), scikit‑learn/statsmodels (metrics, IAA, CIs).
* **Governance**: DVC or LakeFS for large artifacts; Git for manifests and code; signing via GPG/Sigstore.

---

## Project Conventions

### Code Style

* **Formatting & linting**: black (line length 100), ruff (errors, imports, modernizations), isort (imports), mypy (strict, gradual typing).
* **Docstrings**: Google style; every public function/class documents inputs, outputs, side effects, and stability guarantees.
* **Naming**:

  * Package modules use short, action‑oriented names (`kos`, `coverage`, `mapping`, `overlay`, `auditor`, `evals`, `governance`, `cli`, `api`).
  * Types and data classes are nouns (`CoveragePlan`, `MappingRecord`).
  * Functions are verbs and explicit (`allocate_quotas`, `resolve_candidates`).
* **I/O discipline**: pure functions for transforms; side effects isolated in *gateway* and *driver* layers.

### Architecture Patterns

**Overall style**: *Ports & Adapters* (Hexagonal). Core business logic is framework‑agnostic; all external systems (APIs, files, vector stores, LLMs) sit behind stable **ports** with adapter implementations.

**Cross‑cutting standards**

* **Immutability**: artifacts (snapshots, plans, suites) are append‑only and content‑addressed; fixes create new versions.
* **Determinism**: seeds recorded for any sampling; hash of inputs and code saved alongside outputs.
* **Tenancy**: all artifacts and runs are namespaced by tenant/project; no cross‑tenant links unless explicitly approved.
* **Provenance**: every artifact pins upstream versions by ID + hash (e.g., Coverage Plan → KOS snapshot).
* **Licensing**: per‑source license tag and export policy (e.g., “IDs only,” “labels allowed,” “no definitions”). Enforcement happens at the export boundary.

**External connection design (must follow)**

* **Gateway clients** per service (e.g., `OpenAlexGateway`, `WikidataGateway`, `EuroVocSPARQLGateway`, `UMLSUTSGateway`, `LOINCFHIRGateway`, `SnowstormGateway`, `MITRETAXIIGateway`).
* **HTTP discipline**:

  * Set descriptive `User-Agent`.
  * Respect robots/rate‑limits and backoff on 429/5xx with jitter.
  * Use ETag/If‑Modified‑Since where supported; prefer gzip/deflate compression.
  * Enforce request timeouts and circuit breakers; surface clear, typed errors.
  * Cache at the gateway level (content‑hash or request‑hash keys) with TTLs reflective of source update cadences.
* **Version pinning**: persist upstream version/release (e.g., MeSH year, UMLS release, LOINC system‑version, SNOMED edition). No “latest” in production.
* **Pagination**: always implement cursor‑ or page‑based iteration and resumable checkpoints (write progress markers).
* **Data contracts**: gateways normalize to our **canonical concept schema**; never leak raw, source‑specific idiosyncrasies into core modules.
* **Security**: secrets from a manager; mTLS where available; deny open‑web retrieval at runtime unless a context explicitly enables it.
* **Licensing enforcement**: gateways apply redaction/masking policy (e.g., no SNOMED definitions in public reports).

**Data model conventions**

* **Concept IDs**: stable IRIs or CURIEs with a clear prefix (`EV:`, `FIBO:`, `LKIF:`).
* **Overlay IDs**: our namespace (`OV:`), never colliding with base KOS.
* **Paths**: `path_to_root` stored as a list of IDs; do not serialize as strings in core tables.
* **Facets**: enumerated sets (`locale`, `language`, `modality`, `difficulty`, etc.) defined centrally; free‑text is prohibited in core columns.

**Observability**

* **Structured logs** (JSON): include `ts`, `tenant`, `module`, `artifact_id`, `event`, `status`, `duration_ms`, `upstream_source`, `http_status`, `retry_count`, `cache_hit`, `cost_tokens` (for LLM), and `hash`.
* **Metrics**: per‑module throughput, error rates by type, cache hit ratio, mapping ambiguity rate, acceptance rate in overlay review, eval flake rate.
* **Tracing**: each long job (ingest, plan, eval run) emits OpenTelemetry spans; propagate correlation IDs through gateways.

**Error taxonomy (use consistently)**

* `SOURCE_UNAVAILABLE`, `RATE_LIMITED`, `AUTH_FAILED`, `SCHEMA_VIOLATION`, `LICENSING_BLOCK`, `STALE_SNAPSHOT`, `NONDETERMINISTIC_OUTPUT`, `MAPPING_AMBIGUOUS`, `OVERLAY_CONFLICT`, `POLICY_VIOLATION`. Each error includes remediation hints.

**LLM usage policy (applies project‑wide)**

* **Grounded only**: prompts must rely on provided evidence (ontology definitions, sibling labels, curated corpus snippets). No open‑web unless context explicitly allows.
* **Structured output**: strict JSON Schema validation; if invalid and trivially repairable, repair and mark; otherwise re‑ask or escalate.
* **Constrained choice**: mapping and crosswalk prompts may only select from a provided candidate list—never invent IDs.
* **Citations**: required for proposals and judgments (verbatim quotes + source/offset).
* **Determinism**: use low temperature for adjudication; record model/version; rotate order in pairwise judging to avoid position bias.
* **Auditability**: log prompt, schema, model, and evidence hashes.

### Testing Strategy

* **Unit tests**: pure transforms and business logic; high coverage on KOS normalization, stratification, quota allocation, and metric math.
* **Property‑based tests**: mapping resolver (fuzzy/embedding), pairwise generator, quota rounding guaranteeing exact totals.
* **Contract tests**: per gateway using recorded interactions (VCR‑style) and local fixtures; ensure pagination, ETag, and retry logic.
* **Integration tests**: end‑to‑end flows on small fixtures (e.g., EuroVoc subtree → Coverage Plan → Audit → Suite manifest).
* **Golden snapshots**: hash artifacts (Coverage Plan, Suite manifests) to detect unintended changes.
* **LLM protocol tests**: schema‑adherence rate, grounding fidelity, and hallucination rate on calibration sets; fail CI if below thresholds.
* **Non‑functional**: performance SLOs, memory footprint, and determinism checks (repeated runs produce identical hashes).

### Git Workflow

* **Trunk‑based** with short‑lived feature branches.
* **Conventional Commits** (`feat:`, `fix:`, `perf:`, `refactor:`, `ci:`, `docs:`).
* **PR gates**: tests + linters + type checks + artifact diffs; mandatory reviewer for governance‑related changes.
* **Versioning**: semantic versions for code and artifacts; tags on releases; DVC/LakeFS for large data; signed manifests.
* **Release notes**: machine‑generated diffs for plans/suites; human rationale; license/waiver summaries.

---

## Domain Context

* **KOS sources**: EuroVoc (legal/policy), LKIF Core (legal ontology), FIBO (finance ontology), JEL codes (economics), MeSH/LOINC/SNOMED/GO/ChEBI (biomed), ACM CCS & MITRE ATT&CK/CWE/CAPEC (CS/security), MSC/PhySH (math/physics), plus Wikidata and OpenAlex for bibliometric scaffolding.
* **Artifacts & lineage**: every plan/suite/mapping ties back to a **KOS snapshot**; overlay proposals extend coverage without mutating the base KOS; eval slices mirror coverage strata.
* **Evals as PRD**: private evals anchor “what good looks like”; metrics and slices are stable across model versions.

---

## Important Constraints

* **Licensing**: some vocabularies restrict redistribution (e.g., SNOMED CT). The system must be able to **mask labels/definitions** and expose only IDs/counts in public reports.
* **Privacy & safety**: PII/PHI rules apply when source corpora include personal data; enforce de‑identification and jurisdictional residency (EU vs US) at storage and processing layers.
* **Determinism & reproducibility**: no use of “latest” in production; every run pins upstream versions and seeds; artifacts include hashes.
* **Tenancy & isolation**: hard separation per client/project; no cross‑tenant artifact reuse without explicit approval and license compatibility checks.
* **LLM constraints**: LLMs are assistants, not authorities; they must operate under schema/grounding constraints and never invent identifiers.
* **Performance SLOs** (baseline):

  * KOS snapshot (standard dumps): p95 < 30 min.
  * Coverage plan (100k nodes, 4 facets): p95 < 10 min.
  * Mapping throughput: ≥ 50 items/s pre‑LLM; ≥ 2 items/s end‑to‑end with LLM gate (top‑k ≤ 5).
  * Suite generation (slices only): < 5 min.

---

## External Dependencies

> Design external connections using the **Gateway** pattern with the conventions above (User‑Agent, backoff, caching, pagination, version pinning, export policies). Below are the key sources and *how to access them*.

**Cross‑domain scaffolds**

* **OpenAlex (Topics/Concepts)**: public REST; set `User-Agent`; prefer `/topics` for maintained taxonomy; paginate with cursors; cache and record `updated_date`. Use to seed bibliometric coverage or to find literature exemplars.
* **Wikidata SPARQL (WDQS)**: SPARQL endpoint; set `User-Agent`; throttle queries; prefer batched pulls; store the SPARQL text in‑repo for reproducibility; ideal for entity lists and cross‑IDs.
* **EU Vocabularies – EuroVoc**: SPARQL at Publications Office; select `skos:broader`/`narrower` for trees; export CSV/JSON; pin release date in snapshots.
* **LCSH (id.loc.gov)**: HTTP content negotiation to fetch RDF/JSON; no public SPARQL; use as general scaffold where appropriate.

**Finance & economics**

* **FIBO**: download OWL release; load with owlready2; resolve imports; flatten to concept tables; record release version/commit.
* **JEL (AEA)**: AEA site is authoritative; if using third‑party SKOS mirrors, mark as derived and cross‑map back to JEL codes.

**Law & policy**

* **LKIF Core**: public OWL modules; load all for complete coverage; normalize to canonical schema.
* **LegalBench/LexGLUE**: GitHub/Hugging Face for task shapes and sample items; use for eval design, not for KOS.

**Biomedicine & health**

* **UMLS UTS API**: license + API key required; use `/search` (term→CUI) and `/content` (CUI→source‑codes); log release version; respect monthly rate limits.
* **MeSH RDF/SPARQL**: lookup endpoints and SPARQL; track MeSH year; use tree numbers for hierarchical sampling.
* **LOINC FHIR server**: FHIR R4; prefer `ValueSet/$expand` and `CodeSystem/$validate-code`; pin `system-version` to lock to a release; enforce request quotas.
* **SNOMED CT (Snowstorm)**: run a local Snowstorm server (recommended) with licensed RF2 content; use ECL queries for descendants; record edition/version.
* **GO & ChEBI (EBI)**: GO via OWL/OBO/JSON downloads; ChEBI via new REST web services; track releases.

**CS & security**

* **ACM CCS**: ACM’s official structure (2012) as reference; third‑party SKOS mirrors exist—validate and record provenance.
* **MITRE ATT&CK**: TAXII 2.1 server or STIX bundles; fetch collections and objects; record ATT&CK release.

**Credential & directory sources**

* **NPI Registry (CMS)**: public REST; throttle; use for identity/credential cross‑checks of US medical providers.
* **FINRA Developer Center**: dataset APIs require registration; use Query API for supported datasets; BrokerCheck detail is not available as a general public API—do not scrape.
* **SEC Form ADV/IAPD**: use bulk CSVs for reproducible ingestion; site is canonical UI; record snapshot dates.

**Design notes for all external connections**

* **Resumable pagination**: persist cursors/page tokens and resume after failures; never lose progress on long pulls.
* **Backoff & retry**: exponential backoff with jitter on 429/5xx; cap retries; promote `SOURCE_UNAVAILABLE` errors with context.
* **Caching**: request‑hash or URL‑hash cache; respect `Cache-Control`/ETag; set conservative TTLs for unstable sources.
* **Normalization**: map source fields to canonical schema (`concept_id`, `pref_label`, `alt_labels`, `definition`, `parent_id`, `mappings`, `lang`, `deprecated`, `provenance`).
* **Export policies**: enforce license constraints at the gateway—mask or exclude restricted text in downstream artifacts.
* **Security**: no credentials in URLs; OAuth/API keys from secrets manager; mTLS where supported; validate HTTPS certs; deny-list open web unless explicitly enabled.
* **Observability**: every request logs `source`, `route`, `status`, `latency_ms`, `bytes_in/out`, `retry_count`, `backoff_ms`, and `cache_hit`.

---

### Final guidance for AI programming agents

* Prefer **deterministic, standards‑backed** methods; avoid shortcuts that undermine reproducibility.
* Treat **LLM outputs as proposals** bounded by schemas and evidence; never mint or modify authoritative IDs.
* Respect **licenses, residency, and privacy**; export the minimum necessary (IDs and counts) where required.
* Keep **humans in the loop** for structural changes (overlay), policy decisions, and ambiguous mappings.
* Ensure **every artifact is versioned, pinned, diffable, and signed**; all runs must be reproducible from manifests alone.
