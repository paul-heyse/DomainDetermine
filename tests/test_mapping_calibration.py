"""Tests for mapping calibration suite."""

from __future__ import annotations

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
    MappingCalibrationSuite,
    MappingPipeline,
    TextNormalizer,
)
from DomainDetermine.mapping.calibration import CalibrationExample


def fake_llm(payload: str) -> dict[str, str]:
    return {"concept_id": "EV:1", "confidence": "0.95", "evidence": "[]"}


@pytest.fixture
def pipeline(tmp_path: Path, mapping_schema_dir: Path) -> MappingPipeline:
    concept = ConceptEntry(
        concept_id="EV:1",
        pref_label="Competition law",
        definition="Laws about competition",
        language="en",
    )
    repository = ConceptRepository({concept.concept_id: concept})
    generator = CandidateGenerator(repository)
    scorer = CandidateScorer()
    decision = LLMDecisionEngine(model_ref="test", llm_callable=fake_llm, confidence_threshold=0.5)
    crosswalk = CrosswalkProposer(target_schemes=("LKIF",))
    normalizer = TextNormalizer()
    schema_registry = SchemaRegistry(mapping_schema_dir)
    schema_registry.register(
        SchemaRecord(
            name="mapping_decision",
            version="v1",
            schema={
                "type": "object",
                "properties": {
                    "concept_id": {"type": "string"},
                    "confidence": {"type": "string"},
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

        def generate_json(self, schema, prompt: str, *, schema_id: str, max_tokens: int = 256):  # type: ignore[override]
            return {"concept_id": "EV:1", "confidence": "0.95", "evidence": []}

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


def test_calibration_suite_reports_accuracy(pipeline: MappingPipeline) -> None:
    suite = MappingCalibrationSuite(pipeline)
    examples = [CalibrationExample("Competition law", "EV:1")]
    result = suite.run(examples)
    assert result.total == 1
    assert result.correct == 1
    assert result.accuracy == pytest.approx(1.0)
    assert result.metrics["resolution_rate"] == pytest.approx(1.0)
