"""Diagnostics helpers for coverage plans."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Iterable, Mapping, MutableMapping, Sequence

from .models import ConstraintConfig, CoveragePlanDiagnostics, CoveragePlanRow


def _entropy(values: Sequence[int]) -> float:
    """Shannon entropy over quota distribution; higher implies better balance."""
    total = sum(values)
    if total <= 0:
        return 0.0
    result = 0.0
    for value in values:
        if value <= 0:
            continue
        p = value / total
        result -= p * math.log(p, 2)
    return result


def _gini(values: Sequence[int]) -> float:
    """Gini coefficient to flag concentration of quotas in few branches."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    n = len(values)
    cumulative = 0
    weighted_sum = 0
    for index, value in enumerate(sorted_values, start=1):
        cumulative += value
        weighted_sum += index * value
    return (2 * weighted_sum) / (n * cumulative) - (n + 1) / n if cumulative else 0.0


def _quotas_by_facet(rows: Sequence[CoveragePlanRow]) -> Mapping[str, Mapping[str, int]]:
    """Aggregate quotas for each facet value to support fairness dashboards."""
    buckets: MutableMapping[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        for facet_name, facet_value in row.facets.items():
            buckets[facet_name][facet_value] += row.planned_quota
    return {name: dict(counter) for name, counter in buckets.items()}


def build_diagnostics(
    rows: Sequence[CoveragePlanRow],
    constraints: ConstraintConfig,
    total_leaf_count: int,
    leaves_with_quota: Iterable[str],
    orphaned_concepts: Iterable[str],
) -> CoveragePlanDiagnostics:
    """Produce the audit report consumed by Module 5 certification."""
    quotas_by_branch = Counter()
    quotas_by_depth_band = Counter()
    for row in rows:
        quotas_by_branch[row.branch] += row.planned_quota
        quotas_by_depth_band[row.depth_band] += row.planned_quota
    leaf_coverage_ratio = 0.0
    if total_leaf_count:
        leaf_coverage_ratio = len(set(leaves_with_quota)) / total_leaf_count
    red_flags = []
    for row in rows:
        if row.planned_quota == 0:
            red_flags.append(f"Stratum {row.concept_id} has zero quota")  # Highlights starvation.
    for orphan in orphaned_concepts:
        red_flags.append(f"Concept {orphan} excluded without recorded reason")
    for branch, quota in quotas_by_branch.items():
        if constraints.fairness_floor:
            floor_abs = constraints.total_items * constraints.fairness_floor
            if quota < floor_abs:
                red_flags.append(
                    f"Branch {branch} below fairness floor ({quota} vs {floor_abs:.0f})"
                )
        if constraints.fairness_ceiling:
            ceil_abs = constraints.total_items * constraints.fairness_ceiling
            if quota > ceil_abs:
                red_flags.append(
                    f"Branch {branch} exceeds fairness ceiling ({quota} vs {ceil_abs:.0f})"
                )
    return CoveragePlanDiagnostics(
        quotas_by_branch=dict(quotas_by_branch),
        quotas_by_depth_band=dict(quotas_by_depth_band),
        quotas_by_facet=_quotas_by_facet(rows),
        leaf_coverage_ratio=leaf_coverage_ratio,
        entropy=_entropy(list(quotas_by_branch.values())),
        gini_coefficient=_gini(list(quotas_by_branch.values())),
        red_flags=tuple(red_flags),
    )
