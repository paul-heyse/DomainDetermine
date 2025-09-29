"""Eval suite builder orchestrating Module 6 requirements."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .grader import GraderRegistry
from .models import (
    DocumentationPack,
    EvalSuite,
    EvalSuiteManifest,
    GraderReference,
    InstructionPack,
    ItemSchema,
    MetricSpec,
    PolicyPack,
    RunnerConfig,
    ScenarioDefinition,
    SeedDataset,
    SliceDefinition,
)
from .registry import MetricRegistry, SliceRegistry


@dataclass
class EvalSuiteBuilder:
    """Builds evaluation suites from coverage plan derived inputs."""

    slice_registry: SliceRegistry
    metric_registry: MetricRegistry
    grader_registry: GraderRegistry
    manifest_factory: "ManifestFactory" = field(default=None)

    def build_suite(
        self,
        suite_id: str,
        suite_version: str,
        coverage_plan_version: str,
        coverage_plan_snapshot_id: str,
        instruction_pack: InstructionPack,
        policy_pack: PolicyPack,
        slice_definitions: Mapping[str, SliceDefinition],
        scenarios: Mapping[str, ScenarioDefinition],
        item_schemas: Mapping[str, ItemSchema],
        metrics: Mapping[str, MetricSpec],
        runner: RunnerConfig,
        documentation: DocumentationPack,
        seed_datasets: Sequence[SeedDataset],
    ) -> EvalSuite:
        registered_slices: dict[str, SliceDefinition] = {}
        for slice_id, slice_def in slice_definitions.items():
            self.slice_registry.register(slice_def)
            registered_slices[slice_id] = slice_def

        registered_metrics: dict[str, MetricSpec] = {}
        for metric_id, metric in metrics.items():
            self.metric_registry.register(metric)
            registered_metrics[metric_id] = metric

        scenario_map = dict(scenarios)

        graders: dict[str, GraderReference] = {}
        for scenario in scenarios.values():
            for grader_id in scenario.grader_ids:
                reference = self.grader_registry.get_reference(grader_id)
                if not reference:
                    msg = f"Grader '{grader_id}' missing from registry"
                    raise ValueError(msg)
                graders[grader_id] = reference

        manifest_factory = self.manifest_factory or ManifestFactory()
        manifest = manifest_factory.create_manifest(
            suite_id=suite_id,
            suite_version=suite_version,
            coverage_plan_version=coverage_plan_version,
            coverage_plan_snapshot_id=coverage_plan_snapshot_id,
            instruction_pack=instruction_pack,
            policy_pack=policy_pack,
            slices=registered_slices,
            item_schemas=item_schemas,
            graders=graders,
            metrics=registered_metrics,
            runner=runner,
            documentation=documentation,
            seed_datasets=seed_datasets,
        )

        return EvalSuite(
            manifest=manifest,
            slices=registered_slices,
            scenarios=scenario_map,
            graders=graders,
            metrics=registered_metrics,
            item_schemas=dict(item_schemas),
            runner=runner,
            documentation=documentation,
            seed_datasets=tuple(seed_datasets),
        )


@dataclass
class ManifestFactory:
    """Creates manifests with hash tracking."""

    def create_manifest(
        self,
        suite_id: str,
        suite_version: str,
        coverage_plan_version: str,
        coverage_plan_snapshot_id: str,
        instruction_pack: InstructionPack,
        policy_pack: PolicyPack,
        slices: Mapping[str, SliceDefinition],
        item_schemas: Mapping[str, ItemSchema],
        graders: Mapping[str, GraderReference],
        metrics: Mapping[str, MetricSpec],
        runner: RunnerConfig,
        documentation: DocumentationPack,
        seed_datasets: Sequence[SeedDataset],
    ) -> EvalSuiteManifest:
        slice_hashes = {slice_id: slice_def.hash() for slice_id, slice_def in slices.items()}
        item_schema_hashes = {schema_id: schema.hash() for schema_id, schema in item_schemas.items()}
        metric_hashes = {metric_id: metric.hash() for metric_id, metric in metrics.items()}
        seed_dataset_hashes = {dataset.dataset_id: dataset.hash for dataset in seed_datasets}

        return EvalSuiteManifest(
            suite_id=suite_id,
            suite_version=suite_version,
            coverage_plan_version=coverage_plan_version,
            coverage_plan_snapshot_id=coverage_plan_snapshot_id,
            instruction_pack_id=instruction_pack.pack_id,
            policy_pack_id=policy_pack.pack_id,
            slice_hashes=slice_hashes,
            item_schema_hashes=item_schema_hashes,
            grader_hashes={grader_id: grader.code_hash for grader_id, grader in graders.items()},
            metric_hashes=metric_hashes,
            runner_hash=runner.hash(),
            documentation_hash=documentation.hash(),
            seed_dataset_hashes=seed_dataset_hashes,
        )


