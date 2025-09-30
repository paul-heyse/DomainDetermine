from __future__ import annotations

import json
from pathlib import Path

import pytest

from DomainDetermine.llm import ProviderConfig, SchemaRecord, SchemaRegistry, TritonLLMProvider
from DomainDetermine.mapping import (
    CandidateGenerator,
    CandidateScorer,
    ConceptEntry,
    ConceptRepository,
    CrosswalkProposer,
    LLMDecisionEngine,
    MappingContext,
    MappingItem,
    MappingPipeline,
    MappingReport,
    MappingStorage,
    TextNormalizer,
)
from DomainDetermine.prompt_pack import PromptRuntimeManager, RequestBuilder, get_calibration_set
from DomainDetermine.prompt_pack.metrics import MetricsRepository

duckdb = pytest.importorskip("duckdb")  # noqa: F401  # pragma: no cover
pyarrow = pytest.importorskip("pyarrow")  # noqa: F401  # pragma: no cover

PROMPT_PACK_ROOT = Path(__file__).resolve().parents[1] / "src/DomainDetermine/prompt_pack"


def fake_llm(payload: str) -> dict[str, str]:
    data = json.loads(payload)
    return {
        "concept_id": data["candidates"][0],
        "confidence": "0.95",
        "evidence": json.dumps(["Example quote"]),
        "prompt_hash": "abc123",
    }


@pytest.fixture
def concept_repository() -> ConceptRepository:
    concept = ConceptEntry(
        concept_id="EV:1",
        pref_label="Competition law",
        alt_labels=("Antitrust",),
        definition="Laws that promote competition",
        language="en",
        broader=("EV:0",),
        facets={"domain": "competition"},
    )
    return ConceptRepository({concept.concept_id: concept})


@pytest.fixture
def pipeline(concept_repository: ConceptRepository, tmp_path: Path) -> MappingPipeline:
    generator = CandidateGenerator(concept_repository)
    scorer = CandidateScorer()
    decision = LLMDecisionEngine(model_ref="test-model", llm_callable=fake_llm, confidence_threshold=0.8)
    crosswalk = CrosswalkProposer(target_schemes=("LKIF",))
    normalizer = TextNormalizer(acronym_maps={"en": {"EU": "European Union"}})
    schema_registry = SchemaRegistry(tmp_path / "schemas")
    schema_registry.register(
        SchemaRecord(
            name="mapping_decision",
            version="v1",
            schema={
                "type": "object",
                "properties": {
                    "concept_id": {"type": "string"},
                    "confidence": {"type": "string"},
                    "evidence": {"type": "array"},
                },
                "required": ["concept_id", "confidence"],
            },
        )
    )

    class StubProvider(TritonLLMProvider):
        def __init__(self) -> None:
            super().__init__(
                ProviderConfig(
                    endpoint="http://localhost",
                    model_name="test",
                    tokenizer_dir=tmp_path,
                    engine_hash="hash",
                    quantisation="w4a8",
                    readiness_thresholds={
                        "max_queue_delay_us": 100.0,
                        "max_tokens": 500.0,
                        "max_cost_usd": 0.5,
                    },
                    price_per_token=0.0001,
                )
            )
            self.calls: list[tuple[dict[str, object], str]] = []

        def generate_json(self, schema, prompt: str, *, schema_id: str, max_tokens: int = 256):  # type: ignore[override]
            self.calls.append((schema, prompt))
            data = json.loads(prompt)
            return {
                "concept_id": data["candidates"][0],
                "confidence": "0.95",
                "evidence": json.dumps(["Definition snippet"]),
                "prompt_hash": "stub",
            }

        def rank_candidates(self, payload):  # type: ignore[override]
            return {"scores": [0.8 for _ in payload.get("candidates", [])]}

    provider = StubProvider()

    return MappingPipeline(
        normalizer=normalizer,
        generator=generator,
        scorer=scorer,
        decision_engine=decision,
        crosswalk_proposer=crosswalk,
        llm_provider=provider,  # type: ignore[arg-type]
        schema_registry=schema_registry,
        cross_encoder_model="stub",
    )


def test_pipeline_resolves_item(pipeline: MappingPipeline) -> None:
    item = MappingItem("EU competition law", MappingContext(facets={"domain": "competition"}))
    result = pipeline.run([item])
    assert result.records
    record = result.records[0]
    assert record.concept_id == "EV:1"
    assert record.decision_method.value == "llm"
    assert record.evidence_quotes


def test_mapping_storage(tmp_path: Path, pipeline: MappingPipeline) -> None:
    item = MappingItem("EU competition law", MappingContext())
    batch = pipeline.run([item])
    storage = MappingStorage(tmp_path, tmp_path / "mapping.duckdb")
    storage.persist_batch(batch)
    storage.close()
    assert (tmp_path / "mapping_records.parquet").exists()
    assert (tmp_path / "candidate_logs.parquet").exists()
    assert (tmp_path / "crosswalk_proposals.parquet").exists()
    assert json.loads((tmp_path / "metrics.json").read_text())["resolution_rate"] == pytest.approx(1.0)


def test_mapping_report(tmp_path: Path, pipeline: MappingPipeline) -> None:
    item = MappingItem("EU competition law", MappingContext())
    batch = pipeline.run([item])
    report = MappingReport(tmp_path)
    summary_path = report.write_summary(batch)
    data = json.loads(summary_path.read_text())
    assert data["records"] == 1


def test_prompt_runtime_manager_loads_mapping_template() -> None:
    metrics = MetricsRepository()
    manager = PromptRuntimeManager(PROMPT_PACK_ROOT, metrics=metrics)
    runtime = manager.get("mapping_decision", "1.0.0")
    context = {
        "concept_definition": "Competition law governs antitrust.",
        "scope_note": "Applies across EU jurisdictions.",
        "mapping_context": "Sample context that should be filtered out",
    }
    rendered = manager.render_prompt(runtime, context)
    assert "Competition law governs antitrust." in rendered
    result = manager.validate_response(
        runtime,
        {
            "concept_id": "EV:1",
            "confidence": 0.95,
            "evidence": ["Competition law governs antitrust."],
        },
        context=context,
        locale="en-US",
    )
    assert result.metrics["grounding_fidelity"] == 1.0
    snapshot = metrics.as_dict()
    entry = snapshot["mapping_decision:1.0.0"]
    assert entry["locales"]["en-US"]["grounding_fidelity"] == 1.0


def test_request_builder_enforces_policies() -> None:
    metrics = MetricsRepository()
    manager = PromptRuntimeManager(PROMPT_PACK_ROOT, metrics=metrics)
    builder = RequestBuilder(manager)
    context = {
        "concept_definition": "Competition law governs antitrust.",
        "scope_note": "Applies across EU jurisdictions.",
        "mapping_context": "Filtered out",
    }
    request = builder.build("mapping_decision", "1.0.0", context)
    assert "Filtered out" not in request.prompt
    runtime = manager.get("mapping_decision", "1.0.0")
    builder.validate_citations(
        runtime,
        {
            "concept_id": "EV:1",
            "confidence": 0.9,
            "evidence": ["Competition law governs antitrust."],
        },
        request,
    )


def test_request_builder_warmup_uses_calibration() -> None:
    metrics = MetricsRepository()
    manager = PromptRuntimeManager(PROMPT_PACK_ROOT, metrics=metrics)
    builder = RequestBuilder(manager)
    warmup_requests = list(builder.warmup("mapping_decision", "1.0.0"))
    calibration = get_calibration_set("mapping_decision", "1.0.0")
    assert warmup_requests
    assert len(warmup_requests) == len(tuple(calibration))
