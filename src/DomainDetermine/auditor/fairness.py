"""Fairness and balance computation for coverage plans."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Mapping, Optional, Sequence

from DomainDetermine.auditor.models import (
    AuditFinding,
    AuditMetric,
    GateLevel,
    MetricStatus,
    PolicyPack,
)
from DomainDetermine.auditor.utils import copy_record, to_records


def compute_fairness_metrics(
    plan,
    *,
    policy_pack: PolicyPack,
    branch_column: str,
    quota_column: str,
    facet_columns: Sequence[str],
) -> tuple[list[AuditMetric], list[AuditFinding], list[Mapping[str, object]], list[Mapping[str, object]]]:
    """Compute fairness metrics and sparse cell findings."""

    records = to_records(plan)
    dataset = [copy_record(record) for record in records]
    for row in dataset:
        row["fairness_sparse_cells"] = tuple()
    branch_totals: dict[str, float] = defaultdict(float)
    total_quota = 0.0
    quotas: list[float] = []
    for record in records:
        branch = str(record.get(branch_column, "UNKNOWN"))
        quota = float(record.get(quota_column, 0) or 0)
        branch_totals[branch] += quota
        total_quota += quota
        quotas.append(quota)
    total_quota = total_quota or 1.0
    shares = {branch: quota / total_quota for branch, quota in branch_totals.items()}
    entropy_value = _entropy(tuple(shares.values()))
    gini_value = _gini(tuple(quotas))
    hhi_value = sum(value * value for value in shares.values())
    metrics: list[AuditMetric] = [
        _build_metric(
            name="branch_entropy",
            value=entropy_value,
            threshold=None,
            comparator=">",
            status=MetricStatus.PASS,
            gate_level=GateLevel.ADVISORY,
            rationale="Entropy of branch distribution",
            owner="coverage-ops",
        ),
        _build_metric(
            name="branch_gini",
            value=gini_value,
            threshold=None,
            comparator="<",
            status=MetricStatus.PASS,
            gate_level=GateLevel.ADVISORY,
            rationale="Gini coefficient for quotas",
            owner="coverage-ops",
        ),
        _build_metric(
            name="branch_hhi",
            value=hhi_value,
            threshold=None,
            comparator="<",
            status=MetricStatus.PASS,
            gate_level=GateLevel.ADVISORY,
            rationale="Concentration index",
            owner="coverage-ops",
        ),
    ]
    metrics.extend(
        _evaluate_branch_threshold(
            branch=branch,
            share=share,
            policy_pack=policy_pack,
        )
        for branch, share in shares.items()
    )
    findings: list[AuditFinding] = []
    sparse_cells = _detect_sparse_cells(records, facet_columns, quota_column)
    assets: list[Mapping[str, object]] = []
    if sparse_cells:
        metrics.append(
            _build_metric(
                name="sparse_cell_count",
                value=float(len(sparse_cells)),
                threshold=0.0,
                comparator="<=",
                status=MetricStatus.WARN,
                gate_level=GateLevel.ADVISORY,
                rationale="Sparse facet cells detected",
                owner="coverage-ops",
            )
        )
        for cell in sparse_cells:
            findings.append(
                AuditFinding(
                    concept_id=cell["concept_id"],
                    status=MetricStatus.WARN,
                    reasons=("SPARSE_FACET_CELL",),
                    gate_level=GateLevel.ADVISORY,
                )
            )
            for row in dataset:
                if row.get("concept_id") == cell["concept_id"]:
                    row["fairness_sparse_cells"] = tuple(cell["facets"].items())
        assets.append(
            {
                "path": "fairness/sparse_cells.json",
                "content": {"sparse_cells": sparse_cells, "threshold": 1.0},
            }
        )
    return metrics, findings, dataset, assets


def _entropy(values: Sequence[float]) -> float:
    positive = [value for value in values if value > 0]
    if not positive:
        return 0.0
    return float(-sum(value * math.log(value) for value in positive))


def _gini(values: Sequence[float]) -> float:
    positive = sorted(value for value in values if value >= 0)
    n = len(positive)
    if n == 0:
        return 0.0
    cumulative = 0.0
    weighted_sum = 0.0
    for index, value in enumerate(positive, start=1):
        cumulative += value
        weighted_sum += index * value
    if cumulative == 0:
        return 0.0
    return float((2 * weighted_sum) / (n * cumulative) - (n + 1) / n)


def _evaluate_branch_threshold(
    *,
    branch: str,
    share: float,
    policy_pack: PolicyPack,
) -> AuditMetric:
    floor = policy_pack.branch_floors.get(branch)
    ceiling = policy_pack.branch_ceilings.get(branch)
    if floor is not None and share < floor:
        return _build_metric(
            name=f"branch_floor::{branch}",
            value=share,
            threshold=floor,
            comparator=">=",
            status=MetricStatus.FAIL,
            gate_level=GateLevel.BLOCKING,
            rationale="Branch share below floor",
            owner="policy",
        )
    if ceiling is not None and share > ceiling:
        return _build_metric(
            name=f"branch_ceiling::{branch}",
            value=share,
            threshold=ceiling,
            comparator="<=",
            status=MetricStatus.FAIL,
            gate_level=GateLevel.BLOCKING,
            rationale="Branch share above ceiling",
            owner="policy",
        )
    return _build_metric(
        name=f"branch_share::{branch}",
        value=share,
        threshold=None,
        comparator="-",
        status=MetricStatus.PASS,
        gate_level=GateLevel.ADVISORY,
        rationale="Branch share",
        owner="coverage-ops",
    )


def _detect_sparse_cells(
    records: Sequence[Mapping[str, object]],
    facet_columns: Sequence[str],
    quota_column: str,
    threshold: float = 1.0,
) -> list[Mapping[str, object]]:
    if not facet_columns:
        return []
    running_totals: dict[tuple, float] = defaultdict(float)
    ids: dict[tuple, str] = {}
    for record in records:
        key = tuple(record.get(facet, "") for facet in facet_columns)
        concept_id = str(record.get("concept_id"))
        quota = float(record.get(quota_column, 0) or 0)
        running_totals[(concept_id,) + key] += quota
        ids[(concept_id,) + key] = concept_id
    sparse: list[Mapping[str, object]] = []
    for composite_key, value in running_totals.items():
        if value < threshold:
            concept_id, *facet_values = composite_key
            facets = {
                facet: facet_value for facet, facet_value in zip(facet_columns, facet_values)
            }
            sparse.append({"concept_id": concept_id, "facets": facets})
    return sparse


def _build_metric(
    *,
    name: str,
    value: float,
    threshold: Optional[float],
    comparator: str,
    status: MetricStatus,
    gate_level: GateLevel,
    rationale: str,
    owner: str,
) -> AuditMetric:
    return AuditMetric(
        name=name,
        value=float(value),
        threshold=threshold,
        comparator=comparator,
        status=status,
        gate_level=gate_level,
        rationale=rationale,
        owner=owner,
    )


__all__ = ["compute_fairness_metrics"]
