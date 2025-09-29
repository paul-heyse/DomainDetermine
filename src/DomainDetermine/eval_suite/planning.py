"""Suite composition utilities for Module 6."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, MutableMapping, Sequence

from DomainDetermine.coverage_planner.models import CoveragePlan, CoveragePlanRow

from .models import (
    ItemSchema,
    ScenarioDefinition,
    SliceDefinition,
    SliceSamplingConfig,
    hash_payload,
)


@dataclass(frozen=True)
class ScenarioRule:
    """Matching rule that assigns coverage rows to scenarios."""

    scenario_id: str
    description: str
    test_type: str
    item_schema: ItemSchema
    grader_ids: Sequence[str]
    metric_ids: Sequence[str]
    sampling: SliceSamplingConfig
    match_facets: Mapping[str, str]
    match_policy_flags: Sequence[str]

    def matches(self, row: CoveragePlanRow) -> bool:
        for key, value in self.match_facets.items():
            if row.facets.get(key) != value:
                return False
        if self.match_policy_flags:
            if not set(self.match_policy_flags).intersection(row.policy_flags):
                return False
        return True


@dataclass
class SuiteComposer:
    """Transforms coverage plan rows into slices and scenarios."""

    rules: Sequence[ScenarioRule]

    def compose(self, plan: CoveragePlan) -> tuple[MutableMapping[str, SliceDefinition], MutableMapping[str, ScenarioDefinition], MutableMapping[str, ItemSchema]]:
        slices: MutableMapping[str, SliceDefinition] = {}
        scenarios: MutableMapping[str, ScenarioDefinition] = {}
        item_schemas: MutableMapping[str, ItemSchema] = {}

        slice_counter: MutableMapping[str, int] = {}

        for row in plan.rows:
            rule = self._match_rule(row)
            if rule.item_schema.schema_id not in item_schemas:
                item_schemas[rule.item_schema.schema_id] = rule.item_schema

            slice_idx = slice_counter.get(rule.scenario_id, 0) + 1
            slice_counter[rule.scenario_id] = slice_idx
            slice_id = f"{rule.scenario_id}__{slice_idx:04d}"

            provenance_hash = hash_payload(
                {
                    "concept_id": row.concept_id,
                    "facets": dict(row.facets),
                    "policy_flags": list(row.policy_flags),
                    "quota": row.planned_quota,
                    "allocation_method": row.allocation_method,
                }
            )
            coverage_certificate = row.provenance.get("coverage_certificate")
            static_item_hash = None
            if rule.sampling.mode == "static":
                static_item_hash = hash_payload(sorted(rule.sampling.inclusion_list))

            slice_def = SliceDefinition(
                slice_id=slice_id,
                scenario_id=rule.scenario_id,
                concept_id=row.concept_id,
                facets=row.facets,
                difficulty=row.difficulty,
                policy_flags=row.policy_flags,
                quota=row.planned_quota,
                allocation_method=row.allocation_method,
                coverage_certificate=coverage_certificate,
                provenance_hash=provenance_hash,
                sampling=rule.sampling,
                static_item_hash=static_item_hash,
            )
            slices[slice_id] = slice_def

            scenario = scenarios.get(rule.scenario_id)
            if not scenario:
                scenario = ScenarioDefinition(
                    scenario_id=rule.scenario_id,
                    description=rule.description,
                    test_type=rule.test_type,
                    slice_ids=[],
                    grader_ids=list(rule.grader_ids),
                    metric_ids=list(rule.metric_ids),
                    item_schema_id=rule.item_schema.schema_id,
                )
                scenarios[rule.scenario_id] = scenario
            scenario.slice_ids.append(slice_id)

        return slices, scenarios, item_schemas

    def _match_rule(self, row: CoveragePlanRow) -> ScenarioRule:
        for rule in self.rules:
            if rule.matches(row):
                return rule
        raise ValueError(f"No scenario rule matched coverage row {row.concept_id}")


