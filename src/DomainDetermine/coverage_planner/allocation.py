"""Quota allocation strategies for coverage planning."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from .models import AllocationMetadata, AllocationReport, ConstraintConfig, SolverFailureManifest

try:  # pragma: no cover - handled in tests via importorskip
    import pulp
except Exception:  # pylint: disable=broad-except
    pulp = None  # type: ignore[assignment]


@dataclass(frozen=True)
class StratumAllocationInput:
    """Data required to compute allocations for a stratum."""

    stratum_id: str
    branch_id: str
    concept_id: str
    size_weight: float
    variance: Optional[float]
    cost_weight: Optional[float]
    risk_weight: Optional[float]
    minimum: int
    maximum: Optional[int]
    policy_flags: Sequence[str]
    observed_prevalence: Optional[float]


@dataclass
class AllocationResult:
    """Final allocation numbers and audit details for each strategy run."""

    pre_round: Mapping[str, float]
    rounded: Mapping[str, int]
    rounding_delta: Mapping[str, float]
    fairness_notes: Sequence[str]
    deviations: Sequence[str]
    strategy_used: str
    solver_details: Mapping[str, Any] = field(default_factory=dict)
    failure_manifest: Optional[SolverFailureManifest] = None


def _largest_remainder(targets: Mapping[str, float], total: int) -> Dict[str, int]:
    """Deterministic Hamilton method rounding to keep totals exact."""

    floors = {k: math.floor(v) for k, v in targets.items()}
    remainder = total - sum(floors.values())
    ranked = sorted(
        ((targets[k] - floors[k], k) for k in targets),
        key=lambda item: (-item[0], item[1]),
    )
    allocations = floors.copy()
    for _, stratum_id in ranked[: max(remainder, 0)]:
        allocations[stratum_id] += 1
    return allocations


def _rescale(values: MutableMapping[str, float], target_total: int) -> None:
    """Re-normalise fractional allocations after enforcing branch rules."""

    total = sum(values.values())
    if not total:
        fraction = 0.0
    else:
        fraction = target_total / total
    for key in list(values):
        values[key] *= fraction


def _effective_branch_thresholds(
    inputs: Sequence[StratumAllocationInput],
    constraints: ConstraintConfig,
) -> Tuple[Mapping[str, int], Mapping[str, int]]:
    """Return branch-level minimum and maximum quotas after fairness adjustments."""

    minimums: Dict[str, int] = dict(constraints.branch_minimums)
    maximums: Dict[str, int] = dict(constraints.branch_maximums)
    if constraints.fairness_floor is not None:
        floor_count = math.floor(constraints.total_items * constraints.fairness_floor)
        for entry in inputs:
            minimums.setdefault(entry.branch_id, floor_count)
    if constraints.fairness_ceiling is not None:
        ceiling_count = math.ceil(constraints.total_items * constraints.fairness_ceiling)
        for entry in inputs:
            maximums.setdefault(entry.branch_id, ceiling_count)
    return minimums, maximums


def _apply_branch_thresholds(
    raw: MutableMapping[str, float],
    inputs: Sequence[StratumAllocationInput],
    minimums: Mapping[str, int],
    maximums: Mapping[str, int],
    target_total: int,
) -> List[str]:
    """Apply fairness floors/ceilings at the branch level and capture notes."""

    notes: List[str] = []
    branch_map: Dict[str, List[StratumAllocationInput]] = defaultdict(list)
    for entry in inputs:
        branch_map[entry.branch_id].append(entry)
    for branch, minimum in minimums.items():
        current = sum(raw[e.stratum_id] for e in branch_map.get(branch, []))
        if current >= minimum:
            continue
        shortfall = minimum - current
        notes.append(f"Raised branch {branch} by {shortfall} items to meet minimum")
        per_stratum = shortfall / max(len(branch_map.get(branch, [])), 1)
        for entry in branch_map.get(branch, []):
            raw[entry.stratum_id] += per_stratum
    _rescale(raw, target_total)
    for branch, maximum in maximums.items():
        current = sum(raw[e.stratum_id] for e in branch_map.get(branch, []))
        if current <= maximum:
            continue
        excess = current - maximum
        notes.append(f"Reduced branch {branch} by {excess} items to honor maximum")
        per_stratum = excess / max(len(branch_map.get(branch, [])), 1)
        for entry in branch_map.get(branch, []):
            raw[entry.stratum_id] = max(0.0, raw[entry.stratum_id] - per_stratum)
    _rescale(raw, target_total)
    return notes


def _compute_weights(
    inputs: Sequence[StratumAllocationInput],
    constraints: ConstraintConfig,
) -> Dict[str, float]:
    """Return strategy-specific weights per stratum prior to mixing."""

    strategy = constraints.allocation_strategy
    if strategy == "cost_constrained":
        raise ValueError("cost_constrained strategy must be solved via LP")
    weights: Dict[str, float] = {}
    for entry in inputs:
        if strategy == "uniform":
            weight = 1.0
        elif strategy == "proportional":
            weight = max(entry.size_weight, 1e-6)
        elif strategy == "neyman":
            variance = entry.variance if entry.variance is not None else 0.0
            weight = max(entry.size_weight, 1e-6) * max(variance, 1e-6)
        else:
            raise ValueError(f"Unknown allocation strategy: {strategy}")
        if entry.risk_weight is not None:
            weight *= max(entry.risk_weight, 1e-6)
        weights[entry.stratum_id] = weight
    total = sum(weights.values())
    if total <= 0:
        return {entry.stratum_id: 1.0 for entry in inputs}
    return weights


def _apply_prevalence_mixing(
    raw: MutableMapping[str, float],
    inputs: Sequence[StratumAllocationInput],
    constraints: ConstraintConfig,
) -> None:
    """Blend observed prevalence with uniform allocations as configured."""

    if not constraints.observed_prevalence:
        return
    mix = constraints.mixing_parameter
    if mix <= 0.0:
        return
    prevalence_total = sum(constraints.observed_prevalence.values())
    if prevalence_total <= 0:
        return
    normalized_prev = {
        entry.stratum_id: constraints.observed_prevalence.get(entry.concept_id, 0.0) / prevalence_total
        for entry in inputs
    }
    current_total = sum(raw.values())
    if current_total <= 0:
        return
    for entry in inputs:
        existing_ratio = raw[entry.stratum_id] / current_total
        blended = mix * normalized_prev[entry.stratum_id] + (1.0 - mix) * existing_ratio
        raw[entry.stratum_id] = blended * current_total


def _respect_maximums(
    rounded: MutableMapping[str, int],
    inputs: Sequence[StratumAllocationInput],
    total: int,
) -> Sequence[str]:
    """Enforce per-stratum maximums without violating the global budget."""

    notes: List[str] = []
    capacity = {
        entry.stratum_id: (
            entry.maximum - rounded[entry.stratum_id] if entry.maximum is not None else float("inf")
        )
        for entry in inputs
    }
    changed = True
    while changed:
        changed = False
        for entry in inputs:
            maximum = entry.maximum
            if maximum is None:
                continue
            current = rounded[entry.stratum_id]
            if current <= maximum:
                continue
            excess = current - maximum
            rounded[entry.stratum_id] = maximum
            notes.append(f"Capped stratum {entry.stratum_id} at maximum {maximum}")
            receivers = sorted(
                (
                    (capacity.get(other.stratum_id, 0.0), other.stratum_id)
                    for other in inputs
                    if other.stratum_id != entry.stratum_id
                ),
                key=lambda item: (-item[0], item[1]),
            )
            for _, receiver_id in receivers:
                available = capacity.get(receiver_id, 0.0)
                if available <= 0:
                    continue
                take = min(excess, available)
                rounded[receiver_id] += int(take)
                capacity[receiver_id] = max(0.0, available - take)
                excess -= int(take)
                if excess <= 0:
                    break
            if excess > 0:
                raise ValueError("Unable to redistribute quota without violating maximums")
            changed = True
    delta = total - sum(rounded.values())
    if delta != 0:
        adjust_target = max(rounded, key=rounded.get)
        rounded[adjust_target] += delta
        notes.append("Adjusted totals to maintain global budget after maximum enforcement")
    return notes


def _allocate_with_strategy(
    inputs: Sequence[StratumAllocationInput],
    constraints: ConstraintConfig,
) -> AllocationResult:
    """Run the heuristic allocation strategies (uniform/proportional/neyman)."""

    weights = _compute_weights(inputs, constraints)
    denominator = sum(weights.values())
    raw: MutableMapping[str, float] = {
        stratum_id: constraints.total_items * weight / denominator
        for stratum_id, weight in weights.items()
    }
    _apply_prevalence_mixing(raw, inputs, constraints)
    for entry in inputs:
        minimum = entry.minimum
        if raw[entry.stratum_id] < minimum:
            raw[entry.stratum_id] = float(minimum)
    _rescale(raw, constraints.total_items)
    minimums, maximums = _effective_branch_thresholds(inputs, constraints)
    fairness_notes = _apply_branch_thresholds(raw, inputs, minimums, maximums, constraints.total_items)
    rounded = _largest_remainder(raw, constraints.total_items)
    rounding_delta = {
        stratum_id: rounded[stratum_id] - raw[stratum_id]
        for stratum_id in rounded
    }
    deviations = list(_respect_maximums(rounded, inputs, constraints.total_items))
    return AllocationResult(
        pre_round=dict(raw),
        rounded=dict(rounded),
        rounding_delta=rounding_delta,
        fairness_notes=tuple(fairness_notes),
        deviations=tuple(deviations),
        strategy_used=constraints.allocation_strategy,
    )


def _infer_violations(
    inputs: Sequence[StratumAllocationInput],
    constraints: ConstraintConfig,
    minimums: Mapping[str, int],
    maximums: Mapping[str, int],
) -> List[str]:
    """Best-effort heuristics for explaining infeasible LP constraints."""

    messages: List[str] = []
    total_minimum = sum(entry.minimum for entry in inputs)
    if total_minimum > constraints.total_items:
        messages.append(
            f"sum(stratum_minimums)={total_minimum} exceeds total_items={constraints.total_items}"
        )
    for branch, minimum in minimums.items():
        branch_minimum = sum(entry.minimum for entry in inputs if entry.branch_id == branch)
        if branch_minimum > constraints.total_items:
            messages.append(
                f"branch_minimum[{branch}]={branch_minimum} exceeds total_items={constraints.total_items}"
            )
        if minimum > constraints.total_items:
            messages.append(
                f"branch_threshold[{branch}] minimum {minimum} exceeds total_items={constraints.total_items}"
            )
    for branch, maximum in maximums.items():
        if maximum < 0:
            messages.append(f"branch_threshold[{branch}] maximum {maximum} is negative")
    return messages


def _allocate_cost_constrained(
    inputs: Sequence[StratumAllocationInput],
    constraints: ConstraintConfig,
) -> AllocationResult:
    """Solve the cost-constrained optimisation via a deterministic LP solver."""

    minimums, maximums = _effective_branch_thresholds(inputs, constraints)
    solver_details: Dict[str, Any] = {
        "requested_strategy": "cost_constrained",
        "solver": getattr(pulp, "__name__", "pulp") if pulp else None,
    }
    violated: List[str] = []
    try:
        if pulp is None:
            raise RuntimeError("PuLP solver is not installed")

        problem = pulp.LpProblem("coverage_cost_constrained", pulp.LpMaximize)
        variables = {}
        for entry in inputs:
            low_bound = float(entry.minimum)
            up_bound = float(entry.maximum) if entry.maximum is not None else None
            variables[entry.stratum_id] = pulp.LpVariable(
                entry.stratum_id,
                lowBound=low_bound,
                upBound=up_bound,
                cat="Continuous",
            )

        objective_terms = []
        for entry in inputs:
            info = entry.risk_weight if entry.risk_weight is not None else max(entry.size_weight, 1.0)
            cost = entry.cost_weight if entry.cost_weight not in (None, 0.0) else 1.0
            coefficient = info / cost
            objective_terms.append(coefficient * variables[entry.stratum_id])
        problem += pulp.lpSum(objective_terms)

        problem += pulp.lpSum(variables.values()) == constraints.total_items, "total_items"

        branch_variables: Dict[str, List[Any]] = defaultdict(list)
        for entry in inputs:
            branch_variables[entry.branch_id].append(variables[entry.stratum_id])
        for branch, minimum in minimums.items():
            if branch_variables.get(branch):
                problem += pulp.lpSum(branch_variables[branch]) >= minimum, f"min_branch_{branch}"
        for branch, maximum in maximums.items():
            if branch_variables.get(branch):
                problem += pulp.lpSum(branch_variables[branch]) <= maximum, f"max_branch_{branch}"

        time_limit = int(constraints.slos.get("lp_time_limit", 15)) if constraints.slos else 15
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit)
        status_code = problem.solve(solver)
        status = pulp.LpStatus.get(status_code, str(status_code))
        solver_details.update(
            {
                "status": status,
                "solver_name": getattr(solver, "name", "PULP_CBC_CMD"),
                "objective_value": (
                    pulp.value(problem.objective) if status == "Optimal" else None
                ),
            }
        )
        constraint_slacks = {
            name: constraint.slack for name, constraint in problem.constraints.items()
        }
        solver_details["constraint_slacks"] = constraint_slacks
        if status != "Optimal":
            for name, slack in constraint_slacks.items():
                if slack is not None and slack < -1e-6:
                    violated.append(f"{name} slack={slack}")
            raise RuntimeError(f"LP solver exited with status {status}")

        raw: Dict[str, float] = {
            sid: float(variable.value() or 0.0) for sid, variable in variables.items()
        }
        total_raw = sum(raw.values())
        if total_raw and abs(total_raw - constraints.total_items) > 1e-6:
            scale = constraints.total_items / total_raw
            for sid in raw:
                raw[sid] *= scale
    except Exception as exc:  # noqa: BLE001 - propagate failure through manifest
        reason = str(exc)
        if not violated:
            violated = _infer_violations(inputs, constraints, minimums, maximums)
        failure = SolverFailureManifest(
            strategy="cost_constrained",
            reason=reason,
            violated_constraints=tuple(violated) if violated else tuple(),
        )
        fallback_strategy = constraints.fallback_strategy or "uniform"
        fallback_constraints = replace(
            constraints,
            allocation_strategy=fallback_strategy,
        )
        result = _allocate_with_strategy(inputs, fallback_constraints)
        deviations = list(result.deviations)
        deviations.append(f"Fell back to {fallback_strategy} due to LP failure: {reason}")
        result.deviations = tuple(deviations)
        result.failure_manifest = failure
        result.solver_details = {
            **solver_details,
            "status": solver_details.get("status", "Failure"),
            "fallback_strategy": fallback_strategy,
            "reason": reason,
        }
        return result

    objective_value = solver_details.get('objective_value')
    fairness_notes = [
        f"LP objective={objective_value:.4f}" if objective_value is not None else 'LP objective undefined'
    ]
    solver_name = solver_details.get('solver_name', 'unknown')
    fairness_notes.append(f"Solver={solver_name} status={solver_details.get('status')}")
    minimums_note = ', '.join(f"{k}>={v}" for k, v in minimums.items()) or 'none'
    maximums_note = ', '.join(f"{k}<={v}" for k, v in maximums.items()) or 'none'
    fairness_notes.append(f"Branch minima: {minimums_note}; maxima: {maximums_note}")
    rounded = _largest_remainder(raw, constraints.total_items)
    rounding_delta = {
        stratum_id: rounded[stratum_id] - raw[stratum_id]
        for stratum_id in rounded
    }
    deviations = list(_respect_maximums(rounded, inputs, constraints.total_items))
    return AllocationResult(
        pre_round=dict(raw),
        rounded=dict(rounded),
        rounding_delta=rounding_delta,
        fairness_notes=tuple(fairness_notes),
        deviations=tuple(deviations),
        strategy_used="cost_constrained",
        solver_details=solver_details,
    )


def allocate_quotas(
    inputs: Sequence[StratumAllocationInput],
    constraints: ConstraintConfig,
) -> AllocationResult:
    """Allocate quotas across strata according to the requested strategy."""

    constraints.validate()
    if constraints.allocation_strategy == "cost_constrained":
        return _allocate_cost_constrained(inputs, constraints)
    return _allocate_with_strategy(inputs, constraints)


def build_allocation_metadata(
    result: AllocationResult,
    constraints: ConstraintConfig,
) -> AllocationMetadata:
    """Create allocation metadata ready for serialization."""

    parameters: Dict[str, object] = {
        "requested_strategy": constraints.allocation_strategy,
        "mixing_parameter": constraints.mixing_parameter,
        "total_items": constraints.total_items,
    }
    if constraints.branch_minimums:
        parameters["branch_minimums"] = dict(constraints.branch_minimums)
    if constraints.branch_maximums:
        parameters["branch_maximums"] = dict(constraints.branch_maximums)
    if result.strategy_used != constraints.allocation_strategy:
        parameters["fallback_strategy"] = result.strategy_used
    if result.failure_manifest is not None:
        parameters["solver_failure_reason"] = result.failure_manifest.reason
        if result.failure_manifest.violated_constraints:
            parameters["solver_failure_constraints"] = list(
                result.failure_manifest.violated_constraints
            )
    return AllocationMetadata(
        strategy=result.strategy_used,
        pre_round_totals=dict(result.pre_round),
        post_round_totals=dict(result.rounded),
        rounding_deltas=dict(result.rounding_delta),
        parameters=parameters,
        solver_details=dict(result.solver_details),
    )


def build_allocation_report(
    result: AllocationResult,
    constraints: ConstraintConfig,
) -> AllocationReport:
    """Generate a human-readable allocation report."""

    summary = f"Allocated {constraints.total_items} items using {result.strategy_used} strategy"
    solver_status = result.solver_details.get("status") if result.solver_details else None
    if solver_status:
        summary += f" (solver_status={solver_status})"
    fairness_notes = list(result.fairness_notes)
    deviations = list(result.deviations)
    if constraints.fairness_floor:
        fairness_notes.append(
            f"Branch floor: at least {constraints.fairness_floor:.0%} of total per branch"
        )
    if constraints.fairness_ceiling:
        fairness_notes.append(
            f"Branch ceiling: no more than {constraints.fairness_ceiling:.0%} of total per branch"
        )
    if result.failure_manifest is not None:
        deviations.append(
            f"LP failure ({result.failure_manifest.reason}); fallback={result.strategy_used}"
        )
    return AllocationReport(summary=summary, fairness_notes=fairness_notes, deviations=deviations)
