from __future__ import annotations

import logging
from pathlib import Path

import pytest

from DomainDetermine.coverage_planner.models import (
    AllocationMetadata,
    AllocationReport,
    CoveragePlan,
    CoveragePlanDiagnostics,
    CoveragePlanRow,
    CoveragePlanVersion,
    RiskTier,
)
from DomainDetermine.eval_suite import (
    DocumentationPack,
    EvalSuiteBuilder,
    EvalSuitePipeline,
    EvalSuiteRunner,
    EvalSuiteStorage,
    EvalSuiteTelemetry,
    GraderContract,
    GraderRegistry,
    InstructionPack,
    ItemSchema,
    ManifestFactory,
    MetricCalculator,
    MetricRegistry,
    MetricSpec,
    PolicyPack,
    ReportGenerator,
    RunnerConfig,
    ScenarioRule,
    SeedDataset,
    SliceSamplingConfig,
    SuiteComposer,
)
from DomainDetermine.eval_suite.models import GraderReference, SamplingMode
from DomainDetermine.eval_suite.registry import SliceRegistry


@pytest.fixture
def coverage_plan() -> CoveragePlan:
    rows = [
        CoveragePlanRow(
            concept_id="ev:001",
            concept_source="EV",
            path_to_root=("root", "law"),
            depth=2,
            preferred_label="Competition law",
            localized_label="Competition law",
            branch="law",
            depth_band="medium",
            difficulty="hard",
            facets={"locale": "eu", "modality": "analysis"},
            planned_quota=10,
            minimum_quota=5,
            maximum_quota=12,
            allocation_method="proportional",
            rounding_delta=0.0,
            policy_flags=("safety",),
            risk_tier=RiskTier.HIGH,
            cost_weight=None,
            provenance={"coverage_certificate": "cert#1"},
            solver_logs=(),
        ),
        CoveragePlanRow(
            concept_id="ev:002",
            concept_source="EV",
            path_to_root=("root", "finance"),
            depth=2,
            preferred_label="Corporate finance",
            localized_label="Corporate finance",
            branch="finance",
            depth_band="medium",
            difficulty="medium",
            facets={"locale": "us", "modality": "qa"},
            planned_quota=8,
            minimum_quota=4,
            maximum_quota=10,
            allocation_method="uniform",
            rounding_delta=0.0,
            policy_flags=(),
            risk_tier=RiskTier.MEDIUM,
            cost_weight=None,
            provenance={"coverage_certificate": "cert#2"},
            solver_logs=(),
        ),
    ]
    metadata = AllocationMetadata(
        strategy="proportional",
        pre_round_totals={"total": 18.0},
        post_round_totals={"total": 18},
        rounding_deltas={"total": 0.0},
        parameters={"mixing_parameter": 0.3},
    )
    diagnostics = CoveragePlanDiagnostics(
        quotas_by_branch={"law": 10, "finance": 8},
        quotas_by_depth_band={"medium": 18},
        quotas_by_facet={
            "locale": {"eu": 10, "us": 8},
            "modality": {"analysis": 10, "qa": 8},
        },
        leaf_coverage_ratio=1.0,
        entropy=0.7,
        gini_coefficient=0.2,
        red_flags=(),
    )
    allocation_report = AllocationReport(
        summary="Plan built successfully",
        fairness_notes=("Balanced between branches",),
        deviations=(),
    )
    version = CoveragePlanVersion(
        version="1.0.0",
        concept_snapshot_id="snapshot-123",
        created_at=coverage_plan_datetime(),
        author="planner",
        reviewer="auditor",
        changelog=("Initial version",),
    )
    return CoveragePlan(
        rows=rows,
        metadata=metadata,
        diagnostics=diagnostics,
        data_dictionary={"concept_id": "Canonical concept identifier"},
        allocation_report=allocation_report,
        quarantine=(),
        version=version,
        solver_failure=None,
        what_if_runs=(),
        llm_suggestions=(),
    )


def coverage_plan_datetime():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


@pytest.fixture
def scenario_rules() -> list[ScenarioRule]:
    schema = ItemSchema(
        schema_id="schema:classification",
        task_type="classification",
        input_format={"fields": ["prompt", "context"]},
        output_format={"type": "label", "labels": ["yes", "no"]},
        evaluation_notes=("Judge accuracy",),
    )
    rule1 = ScenarioRule(
        scenario_id="scenario:law",
        description="EU competition analysis",
        test_type="classification",
        item_schema=schema,
        grader_ids=("grader:deterministic",),
        metric_ids=("metric:accuracy",),
        sampling=SliceSamplingConfig(
            mode=SamplingMode.STATIC,
            seed=None,
            inclusion_list=("item1", "item2"),
            exclusion_list=(),
        ),
        match_facets={"locale": "eu"},
        match_policy_flags=("safety",),
    )
    rule2 = ScenarioRule(
        scenario_id="scenario:finance",
        description="US finance QA",
        test_type="qa",
        item_schema=schema,
        grader_ids=("grader:deterministic",),
        metric_ids=("metric:accuracy",),
        sampling=SliceSamplingConfig(
            mode=SamplingMode.SEMI_DYNAMIC,
            seed=7,
            inclusion_list=(),
            exclusion_list=(),
        ),
        match_facets={"locale": "us"},
        match_policy_flags=(),
    )
    return [rule1, rule2]


@pytest.fixture
def registry_and_builder(scenario_rules):
    slice_registry = SliceRegistry()
    metric_registry = MetricRegistry()
    metric_registry.register(
        MetricSpec(
            metric_id="metric:accuracy",
            name="Accuracy",
            description="Accuracy of classification",
            slice_threshold=0.8,
            suite_threshold=0.85,
            higher_is_better=True,
            parameters={},
        )
    )
    grader_registry = GraderRegistry()
    grader_registry.register(
        GraderContract(
            grader_id="grader:deterministic",
            grader_type="deterministic",
            normalization_rules={"case": "lower"},
            schema={"type": "string"},
            tolerance={"numeric": 0.0},
            synonym_dictionaries={},
            calibration_targets={},
        ),
        GraderReference(
            grader_id="grader:deterministic",
            grader_type="deterministic",
            code_hash="hash123",
            config_hash="config123",
            description="Deterministic exact match grader",
        ),
    )
    manifest_factory = ManifestFactory()
    builder = EvalSuiteBuilder(
        slice_registry=slice_registry,
        metric_registry=metric_registry,
        grader_registry=grader_registry,
        manifest_factory=manifest_factory,
    )
    composer = SuiteComposer(rules=scenario_rules)
    pipeline = EvalSuitePipeline(
        composer=composer,
        builder=builder,
        metric_registry=metric_registry,
        slice_registry=slice_registry,
        logger=logging.getLogger("eval_suite"),
    )
    return pipeline, builder, slice_registry, metric_registry, grader_registry


def test_pipeline_generates_eval_suite(tmp_path: Path, coverage_plan, registry_and_builder):
    pipeline, builder, slice_registry, metric_registry, grader_registry = registry_and_builder
    instruction_pack = InstructionPack(
        pack_id="instruction:v1",
        version="1",
        description="Legal instructions",
        rubric_reference="rubric.pdf",
        hash="hash-instruction",
    )
    policy_pack = PolicyPack(
        pack_id="policy:v1",
        version="1",
        description="Policy pack",
        policy_hash="policy-hash",
    )
    runner_config = RunnerConfig(
        provider_adapters=("openai",),
        cache_enabled=True,
        cache_scope="suite",
        max_concurrency=2,
        retry_limit=3,
        timeout_seconds=60,
        random_seeds={"execution": 42},
        sandbox_policy={"network": "off"},
    )
    documentation_pack = DocumentationPack(
        summary="Summary",
        methodology="Methodology",
        slice_notes=("Slice note",),
        limitations=("Limitation",),
        license_notices=("License",),
    )
    seed_datasets = [
        SeedDataset(dataset_id="seed:v1", version="1", hash="seed-hash", purpose="calibration")
    ]
    suite = pipeline.generate(
        plan=coverage_plan,
        suite_id="suite:v1",
        suite_version="1.0.0",
        coverage_plan_snapshot_id="snapshot-123",
        instruction_pack=instruction_pack,
        policy_pack=policy_pack,
        runner_config=runner_config,
        documentation_pack=documentation_pack,
        seed_datasets=seed_datasets,
    )
    assert suite.manifest.suite_id == "suite:v1"
    assert suite.metrics
    assert suite.slices
    storage = EvalSuiteStorage(root=tmp_path / "eval")
    manifest_path = storage.save_suite(suite)
    assert manifest_path.exists()
    runner = EvalSuiteRunner(
        config=runner_config,
        metric_calculator=MetricCalculator(bootstrap_samples=10),
        logger=logging.getLogger("runner"),
    )
    predictions = {"metric:accuracy": [1, 0, 1, 1]}
    references = {"metric:accuracy": [1, 0, 0, 1]}
    results = runner.run(suite, predictions=predictions, references=references)
    metrics_path = storage.save_slice_metrics(suite, results)
    assert metrics_path.exists()
    telemetry = EvalSuiteTelemetry(logger=logging.getLogger("telemetry"))
    telemetry.emit_manifest_event(suite.manifest.checksum(), {"suite": suite.manifest.suite_id})
    report = ReportGenerator()
    scorecard = report.build_scorecard(
        suite_id=suite.manifest.suite_id,
        suite_version=suite.manifest.suite_version,
        metrics=results,
    )
    assert scorecard.suite_id == "suite:v1"


