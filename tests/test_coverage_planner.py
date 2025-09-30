
"""Tests for the coverage planner module."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_COVERAGE_PLANNER_TESTS") != "1",
    reason="Coverage planner tests are expensive; set RUN_COVERAGE_PLANNER_TESTS=1 to enable",
)

from DomainDetermine.coverage_planner import (
    ConceptFrameRecord,
    ConstraintConfig,
    CoveragePlanner,
    FacetConfig,
    FacetDefinition,
    PolicyConstraint,
    RiskTier,
)
from DomainDetermine.coverage_planner.combinatorics import generate_pairwise_combinations


@pytest.fixture
def sample_concepts() -> list[ConceptFrameRecord]:
    return [
        ConceptFrameRecord(
            concept_id="root",
            preferred_label="Root",
            path_to_root=("root",),
            depth=0,
            is_leaf=False,
            is_deprecated=False,
        ),
        ConceptFrameRecord(
            concept_id="antitrust.us",
            preferred_label="US Antitrust",
            path_to_root=("root", "antitrust"),
            depth=2,
            is_leaf=True,
            is_deprecated=False,
            domain_attributes={"minimum_quota": 1, "localized_label": "Antitrust (US)"},
            policy_tags=("safety-critical",),
        ),
        ConceptFrameRecord(
            concept_id="competition.eu",
            preferred_label="EU Competition",
            path_to_root=("root", "competition"),
            depth=2,
            is_leaf=True,
            is_deprecated=False,
            domain_attributes={"risk": "medium"},
        ),
        ConceptFrameRecord(
            concept_id="deprecated.node",
            preferred_label="Deprecated",
            path_to_root=("root", "deprecated"),
            depth=2,
            is_leaf=True,
            is_deprecated=True,
        ),
    ]


@pytest.fixture
def facet_config() -> FacetConfig:
    return FacetConfig(
        facets=(
            FacetDefinition(name="locale", values=("US", "EU", "GLOBAL")),
            FacetDefinition(name="modality", values=("text", "speech")),
        ),
        max_combinations=4,
    )


@pytest.fixture
def constraint_config() -> ConstraintConfig:
    return ConstraintConfig(
        total_items=24,
        branch_minimums={"antitrust": 4},
        fairness_floor=0.1,
        fairness_ceiling=0.75,
        observed_prevalence={"antitrust.us": 15, "competition.eu": 5},
        mixing_parameter=0.3,
        variance_estimates={"antitrust.us": 0.4, "competition.eu": 0.2},
        risk_weights={"antitrust.us": 2.0},
        cost_weights={"competition.eu": 1.5},
        allocation_strategy="neyman",
        allocation_version="v0.1",
        concept_snapshot_id="snapshot-123",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        slos={"blocked_jurisdictions": {"locale:GLOBAL"}},
    )


@pytest.fixture
def policy_constraint() -> PolicyConstraint:
    return PolicyConstraint(
        forbidden_policy_tags=("forbidden",),
        jurisdiction_blocks=("locale:GLOBAL",),
    )


def test_pairwise_generator_covers_pairs():
    facets = {"A": ("a1", "a2"), "B": ("b1", "b2"), "C": ("c1", "c2")}
    combinations = generate_pairwise_combinations(facets, invalid_combinations=())
    required_pairs = set()
    names = sorted(facets)
    for i, name_a in enumerate(names):
        for name_b in names[i + 1 :]:
            for value_a in facets[name_a]:
                for value_b in facets[name_b]:
                    required_pairs.add(((name_a, value_a), (name_b, value_b)))
    covered = set()
    for combo in combinations:
        combo_set = set(combo)
        for pair in required_pairs:
            if set(pair).issubset(combo_set):
                covered.add(pair)
    assert covered == required_pairs


def test_coverage_planner_builds_plan_with_budget(sample_concepts, facet_config, constraint_config, policy_constraint):
    planner = CoveragePlanner()
    plan = planner.build_plan(
        concepts=sample_concepts,
        facets=facet_config,
        constraints=constraint_config,
        policy=policy_constraint,
    )

    assert plan.total_quota() == constraint_config.total_items
    quarantined_ids = {record.concept_id for record in plan.quarantine}
    assert "deprecated.node" in quarantined_ids
    assert all(row.rounding_delta in (-1, 0, 1) for row in plan.rows)
    assert any(row.risk_tier == RiskTier.HIGH for row in plan.rows)
    assert "concept_id" in plan.data_dictionary
    assert plan.diagnostics.quotas_by_branch
    assert plan.metadata.post_round_totals
    assert plan.metadata.strategy == constraint_config.allocation_strategy
    assert plan.metadata.parameters["requested_strategy"] == constraint_config.allocation_strategy


def test_blocked_jurisdiction_is_excluded(sample_concepts, facet_config, constraint_config):
    policy = PolicyConstraint(jurisdiction_blocks=("modality:speech",))
    planner = CoveragePlanner()
    plan = planner.build_plan(sample_concepts, facet_config, constraint_config, policy)
    for row in plan.rows:
        assert row.facets.get("modality") == "text"


def test_cost_constrained_uses_lp_solver(sample_concepts, facet_config, policy_constraint):
    pytest.importorskip("pulp")
    constraints = ConstraintConfig(
        total_items=20,
        allocation_strategy="cost_constrained",
        fallback_strategy="proportional",
        cost_weights={"antitrust.us": 2.0, "competition.eu": 1.0},
        risk_weights={"antitrust.us": 4.0, "competition.eu": 1.5},
        allocation_version="v0.2",
        concept_snapshot_id="snapshot-456",
        timestamp=datetime(2024, 2, 1, tzinfo=timezone.utc),
        slos={"lp_time_limit": 5},
    )
    planner = CoveragePlanner()
    plan = planner.build_plan(
        concepts=sample_concepts,
        facets=facet_config,
        constraints=constraints,
        policy=policy_constraint,
    )

    assert plan.metadata.strategy == "cost_constrained"
    assert plan.metadata.parameters["requested_strategy"] == "cost_constrained"
    solver_status = plan.metadata.solver_details.get("status")
    assert solver_status == "Optimal"
    assert plan.solver_failure is None
    assert plan.allocation_report.summary.endswith("solver_status=Optimal")


def test_cost_constrained_records_failure_and_fallback(sample_concepts, facet_config, policy_constraint):
    pytest.importorskip("pulp")
    constraints = ConstraintConfig(
        total_items=1,
        branch_minimums={"antitrust": 3},
        allocation_strategy="cost_constrained",
        fallback_strategy="uniform",
        cost_weights={"antitrust.us": 1.0, "competition.eu": 1.0},
        risk_weights={"antitrust.us": 2.0, "competition.eu": 1.0},
        allocation_version="v0.3",
        concept_snapshot_id="snapshot-789",
        timestamp=datetime(2024, 3, 1, tzinfo=timezone.utc),
        slos={"lp_time_limit": 5},
    )
    planner = CoveragePlanner()
    plan = planner.build_plan(
        concepts=sample_concepts,
        facets=facet_config,
        constraints=constraints,
        policy=policy_constraint,
    )

    assert plan.metadata.strategy == "uniform"
    assert plan.metadata.parameters["requested_strategy"] == "cost_constrained"
    assert plan.metadata.parameters["fallback_strategy"] == "uniform"
    assert plan.solver_failure is not None
    assert "fallback" in plan.allocation_report.deviations[-1]
    assert plan.metadata.parameters["solver_failure_reason"]
