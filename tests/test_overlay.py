from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from DomainDetermine.llm import ProviderConfig, SchemaRecord, SchemaRegistry, TritonLLMProvider
from DomainDetermine.overlay import (
    CandidatePipeline,
    CorpusCandidateMiner,
    CoverageGap,
    EvidenceDocument,
    EvidencePack,
    InternationalizationValidator,
    OverlayLogger,
    OverlayNodeState,
    OverlayProvenance,
    OverlayQualityGateConfig,
    OverlayRegistry,
    PilotAnnotation,
    PilotConfig,
    PilotOrchestrator,
    ReviewDecision,
    ReviewWorkbench,
    RiskControlConfig,
    RiskControlEngine,
)
from DomainDetermine.overlay.exceptions import PolicyViolationError, QualityGateError
from DomainDetermine.overlay.lifecycle import OverlayIdGenerator


@pytest.fixture()
def provenance() -> OverlayProvenance:
    return OverlayProvenance(
        kos_snapshot_id="snapshot-1",
        prompt_template_hash="prompt-hash",
        evidence_pack_hash="evidence-hash",
        llm_model_ref="gpt-test",
        created_by="pipeline",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


@pytest.fixture()
def overlay_llm(tmp_path: Path) -> tuple[TritonLLMProvider, SchemaRegistry]:
    schemas = SchemaRegistry(tmp_path / "schemas")
    schemas.register(
        SchemaRecord(
            name="overlay_candidate",
            version="v1",
            description="Schema for overlay candidate proposals",
            schema={
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "justification": {"type": "string"},
                    "citations": {"type": "array", "items": {"type": "string"}},
                    "annotation_prompts": {"type": "array", "items": {"type": "string"}},
                    "difficulty": {"type": "string"},
                    "nearest_existing": {"type": ["string", "null"]},
                    "split_children": {"type": "array", "items": {"type": "string"}},
                    "merge_targets": {"type": "array", "items": {"type": "string"}},
                    "synonyms": {"type": "object"},
                    "jurisdiction_tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "label",
                    "justification",
                    "citations",
                    "annotation_prompts",
                    "difficulty",
                    "nearest_existing",
                    "split_children",
                    "merge_targets",
                    "synonyms",
                    "jurisdiction_tags",
                ],
            },
        )
    )

    class StubProvider(TritonLLMProvider):
        def __init__(self) -> None:
            super().__init__(
                ProviderConfig(
                    endpoint="http://localhost",
                    model_name="overlay",
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
            self.last_payload = None

        def generate_json(self, schema, prompt: str, *, schema_id: str, max_tokens: int = 256):  # type: ignore[override]
            self.last_payload = json.loads(prompt)
            return {
                "label": "Merger Notification Threshold",
                "justification": "Supported by provided filings",
                "citations": ["base-1"],
                "annotation_prompts": ["Does the document mention notification thresholds?"],
                "difficulty": "advanced",
                "nearest_existing": None,
                "split_children": [],
                "merge_targets": [],
                "synonyms": {"en": ["Merger Control Threshold"]},
                "jurisdiction_tags": ["EU"],
            }

    provider = StubProvider()
    return provider, schemas


def test_overlay_registry_lifecycle(provenance: OverlayProvenance) -> None:
    registry = OverlayRegistry()
    evidence_pack = EvidencePack(documents=(EvidenceDocument("doc1", "Example", 0, 7),))
    node = registry.register_candidate(
        base_concept_id="base-1",
        preferred_labels={"en": "New Concept"},
        alt_labels=None,
        short_definition="A new overlay concept",
        long_definition=None,
        examples=("Example usage",),
        difficulty="intermediate",
        jurisdiction_tags=("global",),
        evidence_pack=evidence_pack,
        provenance=provenance,
    )
    assert node.state is OverlayNodeState.CANDIDATE

    registry.transition(
        node.overlay_id,
        to_state=OverlayNodeState.APPROVED,
        reviewer_id="reviewer-1",
        rationale="looks good",
    )
    registry.transition(
        node.overlay_id,
        to_state=OverlayNodeState.PUBLISHED,
        reviewer_id="reviewer-1",
        rationale="pilot pass",
    )

    manifest = registry.build_manifest(version="v1")
    assert manifest.nodes[0].overlay_id == node.overlay_id
    delta = registry.build_coverage_delta(
        node.overlay_id,
        coverage_plan_id="plan-1",
        planned_quota=10,
        risk_tier="low",
    )
    assert delta.preferred_label == "New Concept"
    assert delta.planned_quota == 10


def test_candidate_pipeline_generates_valid_proposal(provenance: OverlayProvenance, overlay_llm) -> None:
    provider, registry = overlay_llm
    miner = CorpusCandidateMiner()
    gap = CoverageGap(
        parent_concept_id="base-1",
        parent_label="Corporate Transactions",
        desired_facets={"locale": "en-US"},
        corpus_snippets=(("Important Merger Control Filing"),),
        editorial_rules=("Use noun phrases",),
        policy_guardrails=("No restricted category",),
    )
    seeds = miner.extract(gap)
    assert seeds

    pipeline = CandidatePipeline(llm_provider=provider, schema_registry=registry, quality_config=OverlayQualityGateConfig())
    evidence_documents = (EvidenceDocument("base-1", "Filing referenced", 0, 18),)
    proposal = pipeline.generate_proposal(
        gap=gap,
        parent_definition="Parent definition",
        sibling_labels=("Corporate Merger",),
        mining_candidates=seeds,
        existing_labels=("Corporate Merger",),
        evidence_documents=evidence_documents,
    )
    assert proposal.structured.label == "Merger Notification Threshold"
    assert proposal.prompt_hash


def test_candidate_pipeline_duplicate_rejected(provenance: OverlayProvenance, overlay_llm) -> None:
    provider, registry = overlay_llm
    gap = CoverageGap(
        parent_concept_id="base-1",
        parent_label="Corporate Transactions",
        desired_facets={},
        corpus_snippets=("Example",),
        editorial_rules=tuple(),
        policy_guardrails=tuple(),
    )

    class RejectingProvider(TritonLLMProvider):
        def __init__(self, config: ProviderConfig) -> None:
            super().__init__(config)

        def generate_json(self, schema, prompt: str, *, schema_id: str, max_tokens: int = 256):  # type: ignore[override]
            return {
                "label": "Existing Concept",
                "justification": "",
                "citations": [],
                "annotation_prompts": [""],
                "difficulty": "basic",
                "nearest_existing": "Existing Concept",
                "split_children": [],
                "merge_targets": [],
                "synonyms": {},
                "jurisdiction_tags": [],
            }

    rejecting_provider = RejectingProvider(
        ProviderConfig(
            endpoint=provider.config.endpoint,
            model_name=provider.config.model_name,
            tokenizer_dir=provider.config.tokenizer_dir,
            engine_hash=provider.config.engine_hash,
            quantisation=provider.config.quantisation,
            readiness_thresholds={
                "max_queue_delay_us": 100.0,
                "max_tokens": 500.0,
                "max_cost_usd": 0.5,
            },
            price_per_token=0.0001,
        )
    )
    pipeline = CandidatePipeline(llm_provider=rejecting_provider, schema_registry=registry)
    evidence_documents = (EvidenceDocument("doc", "", None, None),)
    with pytest.raises(QualityGateError):
        pipeline.generate_proposal(
            gap=gap,
            parent_definition="Parent",
            sibling_labels=tuple(),
            mining_candidates=tuple(),
            existing_labels=("Existing Concept",),
            evidence_documents=evidence_documents,
        )


def test_reviewer_workbench_and_pilot_flow(provenance: OverlayProvenance) -> None:
    registry = OverlayRegistry()
    evidence_pack = EvidencePack(documents=(EvidenceDocument("doc1", "Example", 0, 7),))
    node = registry.register_candidate(
        base_concept_id="base-1",
        preferred_labels={"en": "Overlay Concept"},
        alt_labels=None,
        short_definition="Detailed summary",
        long_definition=None,
        examples=("Example usage",),
        difficulty="advanced",
        jurisdiction_tags=("global",),
        evidence_pack=evidence_pack,
        provenance=provenance,
    )

    workbench = ReviewWorkbench(registry)
    view = workbench.present(node.overlay_id, sibling_labels=("Sibling",))
    assert view.overlay_id == node.overlay_id
    record = workbench.submit_decision(
        node.overlay_id,
        reviewer_id="reviewer-1",
        decision=ReviewDecision.ACCEPT,
        rationale="High quality",
    )
    assert record.decision is ReviewDecision.ACCEPT

    pilot = PilotOrchestrator(registry)
    samples = (
        PilotAnnotation(item_id="1", annotations=("yes", "yes"), durations_seconds=(5.0, 6.0)),
        PilotAnnotation(item_id="2", annotations=("yes", "yes"), durations_seconds=(4.0, 5.0)),
    )
    result = pilot.run_pilot(
        node.overlay_id,
        config=PilotConfig(sample_size=2, iaa_threshold=0.8, throughput_threshold=10.0),
        samples=samples,
        reviewer_id="reviewer-1",
    )
    assert result.passes
    assert registry.get(node.overlay_id).state is OverlayNodeState.PUBLISHED


def test_overlay_observability_and_risk_controls() -> None:
    logger = OverlayLogger()
    logger.log_prompt(
        overlay_id="overlay:1",
        prompt_hash="prompt",
        evidence_hash="evidence",
        response_payload="{}",
        model="gpt-test",
        latency_ms=100.0,
        tenant="tenant-1",
    )
    logger.log_decision(
        overlay_id="overlay:1",
        reviewer_id="rev",
        decision="accept",
        latency_ms=1_000.0,
        rationale=None,
    )
    logger.log_decision(
        overlay_id="overlay:2",
        reviewer_id="rev",
        decision="reject",
        latency_ms=100_000.0,
        rationale="missing evidence",
    )
    metrics = logger.metrics()
    assert 0.0 <= metrics.acceptance_rate <= 1.0
    assert metrics.rejection_reasons["reject"] == 1

    evidence_pack = EvidencePack(documents=(EvidenceDocument("doc", "Snippet", 0, 6),))
    risk_engine = RiskControlEngine(
        RiskControlConfig(forbidden_terms=("forbidden",), protected_categories=("sensitive",))
    )
    signals = risk_engine.evaluate(
        candidate_label="Forbidden Concept",
        justification="Covers sensitive data",
        evidence_pack=evidence_pack,
    )
    assert any(signal.risk_type == "policy" for signal in signals)
    with pytest.raises(PolicyViolationError):
        risk_engine.enforce(signals)


def test_internationalization_duplicate_detection(provenance: OverlayProvenance) -> None:
    registry = OverlayRegistry()
    evidence_pack = EvidencePack(documents=(EvidenceDocument("doc", "Example", 0, 7),))
    first = registry.register_candidate(
        base_concept_id="base-1",
        preferred_labels={"en": "Data Protection"},
        alt_labels=None,
        short_definition="Summary",
        long_definition=None,
        examples=tuple(),
        difficulty="basic",
        jurisdiction_tags=("global",),
        evidence_pack=evidence_pack,
        provenance=provenance,
    )
    second = registry.register_candidate(
        base_concept_id="base-1",
        preferred_labels={"fr": "Protection des Données"},
        alt_labels=None,
        short_definition="Résumé",
        long_definition=None,
        examples=tuple(),
        difficulty="basic",
        jurisdiction_tags=("global",),
        evidence_pack=evidence_pack,
        provenance=provenance,
    )
    validator = InternationalizationValidator(duplicate_threshold=0.2)
    collisions = validator.detect_cross_lingual_duplicates([first, second])
    assert collisions


def test_overlay_id_generator_uniqueness() -> None:
    generator = OverlayIdGenerator(namespace="overlay")
    identifier1 = generator.generate("Example Label")
    identifier2 = generator.generate("Example Label")
    assert identifier1 != identifier2
