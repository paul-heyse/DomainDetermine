"""Utilities for reducing facet combinations via pairwise coverage."""

from __future__ import annotations

from itertools import product
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

FacetSelection = Tuple[Tuple[str, str], ...]


def _normalize_combination(combo: Iterable[Tuple[str, str]]) -> FacetSelection:
    """Return a canonical ordering for facet selections to simplify comparisons."""
    return tuple(sorted(combo, key=lambda item: item[0]))


def _is_invalid(combo: FacetSelection, invalid_sets: Sequence[Sequence[Tuple[str, str]]]) -> bool:
    """Check whether a combination violates a policy-defined invalid set."""
    frozen_combo = set(combo)
    for invalid in invalid_sets:
        invalid_set = set(invalid)
        if invalid_set.issubset(frozen_combo):
            return True
    return False


def _all_pairs(mapping: Mapping[str, Sequence[str]]) -> List[FacetSelection]:
    """Enumerate every facet-value pair needed for pairwise coverage."""
    pairs: List[FacetSelection] = []
    facet_names = list(mapping)
    for i, name_a in enumerate(facet_names):
        for name_b in facet_names[i + 1 :]:
            for value_a in mapping[name_a]:
                for value_b in mapping[name_b]:
                    pairs.append(_normalize_combination(((name_a, value_a), (name_b, value_b))))
    return pairs


def generate_pairwise_combinations(
    facets: Mapping[str, Sequence[str]],
    invalid_combinations: Sequence[Sequence[Tuple[str, str]]],
) -> List[FacetSelection]:
    """Generate deterministic combinations that cover valid facet pairs for audits."""

    all_pairs = [pair for pair in _all_pairs(facets) if not _is_invalid(pair, invalid_combinations)]
    uncovered = set(all_pairs)
    if not uncovered:
        return []

    facet_names = list(facets.keys())
    combinations: List[FacetSelection] = []

    while uncovered:
        working: Dict[str, str] = {}
        for facet_name in facet_names:
            # Greedy heuristic: choose the value covering the largest number of uncovered pairs.
            best_value = None
            best_score = -1
            for value in facets[facet_name]:
                candidate = _normalize_combination(tuple(working.items()) + ((facet_name, value),))
                if _is_invalid(candidate, invalid_combinations):
                    continue
                covered_pairs = sum(
                    1 for pair in uncovered if set(pair).issubset(set(candidate))
                )
                if covered_pairs > best_score:
                    best_score = covered_pairs
                    best_value = value
            if best_value is None:
                best_value = facets[facet_name][0]
            working[facet_name] = best_value
        normalized = _normalize_combination(tuple(working.items()))
        if _is_invalid(normalized, invalid_combinations):
            # If greedy selection hits an invalid junction, fall back to admissible Cartesian search.
            for full_combo in product(*[facets[name] for name in facet_names]):
                candidate = _normalize_combination(zip(facet_names, full_combo))
                if not _is_invalid(candidate, invalid_combinations):
                    normalized = candidate
                    break
        combinations.append(normalized)
        uncovered -= {pair for pair in list(uncovered) if set(pair).issubset(set(normalized))}

    combinations.sort()  # Stable ordering keeps outputs reproducible for downstream diffs.
    return combinations


def expand_full_cartesian(
    facets: Mapping[str, Sequence[str]],
    invalid_combinations: Sequence[Sequence[Tuple[str, str]]],
) -> List[FacetSelection]:
    """Return the full Cartesian product minus invalid combinations for small grids."""

    facet_names = list(facets)
    raw: List[FacetSelection] = []
    for values in product(*[facets[name] for name in facet_names]):
        combo = _normalize_combination(zip(facet_names, values))
        if _is_invalid(combo, invalid_combinations):
            continue
        raw.append(combo)
    return raw
