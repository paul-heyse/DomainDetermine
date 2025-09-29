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

duckdb = pytest.importorskip("duckdb")  # noqa: F401  # pragma: no cover
pyarrow = pytest.importorskip("pyarrow")  # noqa: F401  # pragma: no cover


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
    )
    return ConceptRepository({concept.concept_id: concept})


@pytest.fixture
def pipeline(concept_repository: ConceptRepository, tmp_path: Path) -> MappingPipeline:
    generator = CandidateGenerator(concept_repository)
    scorer = CandidateScorer()
    decision = LLMDecisionEngine(model_ref="test-model", llm_callable=fake_llm, confidence_threshold=0.8)
    crosswalk = CrosswalkProposer(target_schemes=("LKIF",))
    normalizer = TextNormalizer()
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

    class StubProvider:
        def __init__(self) -> None:
            self.calls: list[tuple[dict[str, object], str]] = []

        def generate_json(self, schema, prompt: str, max_tokens: int = 256):
            self.calls.append((schema, prompt))
            data = json.loads(prompt)
            return {
                "concept_id": data["candidates"][0],
                "confidence": "0.95",
                "evidence": json.dumps(["Definition snippet"]),
                "prompt_hash": "stub",
            }

    provider = StubProvider()

    return MappingPipeline(
        normalizer=normalizer,
        generator=generator,
        scorer=scorer,
        decision_engine=decision,
        crosswalk_proposer=crosswalk,
        llm_provider=provider,  # type: ignore[arg-type]
        schema_registry=schema_registry,
    )


def test_pipeline_resolves_item(pipeline: MappingPipeline) -> None:
    item = MappingItem("EU competition law", MappingContext())
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


