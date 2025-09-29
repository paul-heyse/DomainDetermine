"""High-level orchestration pipeline for Module 6."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from DomainDetermine.coverage_planner.models import CoveragePlan

from .builder import EvalSuiteBuilder
from .models import (
    DocumentationPack,
    EvalSuite,
    InstructionPack,
    PolicyPack,
    RunnerConfig,
    SeedDataset,
)
from .planning import SuiteComposer
from .registry import MetricRegistry, SliceRegistry


@dataclass
class EvalSuitePipeline:
    """End-to-end pipeline turning coverage plans into evaluation suites."""

    composer: SuiteComposer
    builder: EvalSuiteBuilder
    metric_registry: MetricRegistry
    slice_registry: SliceRegistry
    logger: logging.Logger

    def generate(
        self,
        plan: CoveragePlan,
        suite_id: str,
        suite_version: str,
        coverage_plan_snapshot_id: str,
        instruction_pack: InstructionPack,
        policy_pack: PolicyPack,
        runner_config: RunnerConfig,
        documentation_pack: DocumentationPack,
        seed_datasets: Sequence[SeedDataset],
    ) -> EvalSuite:
        self.logger.info(
            "eval_suite.pipeline.start",
            extra={
                "suite_id": suite_id,
                "suite_version": suite_version,
                "coverage_plan_version": plan.version.version,
            },
        )
        slices, scenarios, item_schemas = self.composer.compose(plan)

        metrics = dict(self.metric_registry.all())
        self.logger.info(
            "eval_suite.pipeline.metrics",
            extra={"metric_ids": list(metrics)},
        )
        eval_suite = self.builder.build_suite(
            suite_id=suite_id,
            suite_version=suite_version,
            coverage_plan_version=plan.version.version,
            coverage_plan_snapshot_id=coverage_plan_snapshot_id,
            instruction_pack=instruction_pack,
            policy_pack=policy_pack,
            slice_definitions=slices,
            scenarios=scenarios,
            item_schemas=item_schemas,
            metrics=metrics,
            runner=runner_config,
            documentation=documentation_pack,
            seed_datasets=seed_datasets,
        )
        self.logger.info(
            "eval_suite.pipeline.complete",
            extra={"suite_manifest_hash": eval_suite.manifest.checksum()},
        )
        return eval_suite


