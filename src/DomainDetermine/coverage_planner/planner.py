"""Core planner that constructs coverage plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from typing import Dict, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from .allocation import (
    AllocationResult,
    StratumAllocationInput,
    allocate_quotas,
    build_allocation_metadata,
    build_allocation_report,
)
from .combinatorics import expand_full_cartesian, generate_pairwise_combinations
from .diagnostics import build_diagnostics
from .models import (
    ConceptFrameRecord,
    ConstraintConfig,
    CoveragePlan,
    CoveragePlanDiagnostics,
    CoveragePlanRow,
    CoveragePlanVersion,
    FacetConfig,
    LlmSuggestion,
    PolicyConstraint,
    QuarantineRecord,
    RiskTier,
)


@dataclass
class PlannerConfig:
    """Configuration options for the coverage planner."""

    concept_source: str = "module-1"
    author: str = "coverage-planner"
    reviewer: Optional[str] = None
    max_combinations: Optional[int] = None
    tree_policy: str = "leaves-only"


class CoveragePlanner:
    """Builds coverage plans by combining concepts, facets, and constraints."""

    def __init__(self, config: Optional[PlannerConfig] = None) -> None:
        self.config = config or PlannerConfig()
        if self.config.tree_policy not in {"leaves-only", "mixed"}:
            msg = "tree_policy must be 'leaves-only' or 'mixed'"
            raise ValueError(msg)
        self._coverage_certificates: Dict[Tuple[Tuple[str, str], ...], Tuple[Tuple[Tuple[str, str], ...], ...]] = {}
        self._blocked_combinations_log: List[Dict[str, object]] = []
        self._blocked_combinations_seen: set[Tuple[Tuple[str, str], ...]] = set()
        self._configured_invalid_combinations: Tuple[Tuple[Tuple[str, str], ...], ...] = tuple()

    def build_plan(
        self,
        concepts: Sequence[ConceptFrameRecord],
        facets: FacetConfig,
        constraints: ConstraintConfig,
        policy: PolicyConstraint,
        *,
        llm_suggestions: Sequence[LlmSuggestion] = (),
    ) -> CoveragePlan:
        """Construct a coverage plan artefact from canonical concepts and constraints."""

        self._coverage_certificates.clear()
        self._blocked_combinations_log.clear()
        self._blocked_combinations_seen.clear()
        for facet in facets.facets:
            facet.validate()
        sanitized_concepts, quarantine = self._filter_policy(concepts, policy)
        selected_concepts = self._apply_tree_policy(sanitized_concepts)
        facet_combinations = self._generate_facet_grid(facets)
        # Keeps the stratum count tractable by switching to pairwise coverage when needed.
        fan_out = self._compute_fan_out(concepts)
        # Fan-out approximates branch breadth; doubles as a difficulty heuristic.
        difficulty_overrides = self._apply_llm_suggestions(llm_suggestions, selected_concepts)
        # LLM adjustments only land when a reviewer has approved them.
        strata_inputs, plan_rows = self._build_strata(
            selected_concepts,
            facet_combinations,
            constraints,
            policy,
            fan_out,
            difficulty_overrides,
        )
        allocation = allocate_quotas(strata_inputs, constraints)
        # Deterministic allocation ensures the plan can be reproduced alongside manifests.
        plan_rows = self._merge_allocations(plan_rows, allocation, constraints)
        diagnostics = self._build_diagnostics(plan_rows, concepts, quarantine, constraints)
        metadata = build_allocation_metadata(allocation, constraints)
        metadata.parameters = dict(metadata.parameters)
        metadata.solver_details = dict(metadata.solver_details)
        if allocation.solver_details:
            metadata.solver_details.update(allocation.solver_details)
            metadata.parameters["solver_status"] = allocation.solver_details.get("status")
        if allocation.failure_manifest is not None:
            metadata.parameters["solver_failure_timestamp"] = allocation.failure_manifest.timestamp.isoformat()
        metadata.parameters["llm_rejections"] = difficulty_overrides["rejections"]
        metadata.parameters["tree_policy"] = self.config.tree_policy
        metadata.parameters["coverage_strength"] = facets.coverage_strength
        metadata.parameters["invalid_combinations"] = [
            [list(pair) for pair in invalid]
            for invalid in self._configured_invalid_combinations
        ]
        metadata.parameters["blocked_combinations"] = self._blocked_combinations_log
        metadata.parameters["prevalence_snapshot_id"] = constraints.prevalence_snapshot_id
        allocation_report = build_allocation_report(allocation, constraints)
        version = CoveragePlanVersion(
            version=constraints.allocation_version,
            concept_snapshot_id=constraints.concept_snapshot_id,
            created_at=constraints.timestamp,
            author=self.config.author,
            reviewer=self.config.reviewer,
            changelog=tuple(allocation.deviations),
        )
        data_dictionary = self._build_data_dictionary()
        plan = CoveragePlan(
            rows=plan_rows,
            metadata=metadata,
            diagnostics=diagnostics,
            data_dictionary=data_dictionary,
            allocation_report=allocation_report,
            quarantine=quarantine,
            version=version,
            solver_failure=allocation.failure_manifest,
            what_if_runs=tuple(),
            llm_suggestions=tuple(llm_suggestions),
        )
        return plan

    def _apply_tree_policy(
        self, concepts: Sequence[ConceptFrameRecord]
    ) -> List[ConceptFrameRecord]:
        if self.config.tree_policy == "leaves-only":
            return [concept for concept in concepts if concept.is_leaf]
        return list(concepts)

    def _filter_policy(
        self,
        concepts: Sequence[ConceptFrameRecord],
        policy: PolicyConstraint,
    ) -> Tuple[List[ConceptFrameRecord], List[QuarantineRecord]]:
        """Apply handbook policy rules and track excluded concepts."""

        usable: List[ConceptFrameRecord] = []
        quarantine: List[QuarantineRecord] = []
        for concept in concepts:
            if concept.is_deprecated:
                quarantine.append(
                    QuarantineRecord(concept.concept_id, "deprecated", {"path": concept.path_to_root})
                )
                continue
            if policy.concept_is_forbidden(concept):
                quarantine.append(
                    QuarantineRecord(concept.concept_id, "forbidden", {"tags": concept.policy_tags})
                )
                continue
            usable.append(concept)
        return usable, quarantine

    def _generate_facet_grid(self, facets: FacetConfig) -> List[Mapping[str, str]]:
        """Return facet combinations respecting invalid pairs and coverage limits."""

        mapping = facets.as_mapping()
        if not mapping:
            return [dict()]
        self._configured_invalid_combinations = tuple(
            tuple(tuple(pair) for pair in invalid) for invalid in facets.invalid_combinations
        )
        full_size = 1
        for values in mapping.values():
            full_size *= len(values)
        max_combinations = self.config.max_combinations or facets.max_combinations
        if facets.coverage_strength <= 1 or full_size <= max_combinations:
            combos = expand_full_cartesian(mapping, facets.invalid_combinations)
        else:
            combos = generate_pairwise_combinations(mapping, facets.invalid_combinations)
        results: List[Mapping[str, str]] = []
        for combo in combos:
            normalized = tuple(sorted(combo, key=lambda item: item[0]))
            certificate = self._build_coverage_certificate(
                normalized,
                facets.coverage_strength,
            )
            self._coverage_certificates[normalized] = certificate
            results.append(dict(combo))
        return results

    def _compute_fan_out(
        self, concepts: Sequence[ConceptFrameRecord]
    ) -> Mapping[str, int]:
        counts: MutableMapping[str, int] = {}
        for concept in concepts:
            for ancestor in concept.path_to_root[:-1]:
                counts[ancestor] = counts.get(ancestor, 0) + 1
        return counts

    def _apply_llm_suggestions(
        self,
        suggestions: Sequence[LlmSuggestion],
        concepts: Sequence[ConceptFrameRecord],
    ) -> Dict[str, List[str]]:
        """Validate optional LLM refinements against reviewer approval rules."""

        overrides: Dict[str, str] = {}
        rejections: List[Dict[str, object]] = []
        concept_index = {concept.concept_id: concept for concept in concepts}
        for suggestion in suggestions:
            if suggestion.concept_id not in concept_index:
                rejections.append(
                    {
                        "concept_id": suggestion.concept_id,
                        "reason": "unknown_concept",
                        "reviewer": suggestion.approved_by,
                    }
                )
                continue
            if not suggestion.is_approved():
                rejections.append(
                    {
                        "concept_id": suggestion.concept_id,
                        "reason": "not_approved",
                        "reviewer": suggestion.approved_by,
                    }
                )
                continue
            if suggestion.proposal_type == "difficulty_adjustment":
                new_difficulty = suggestion.payload.get("difficulty")
                if isinstance(new_difficulty, str):
                    overrides[suggestion.concept_id] = new_difficulty
                else:
                    rejections.append(
                        {
                            "concept_id": suggestion.concept_id,
                            "reason": "invalid_payload",
                            "reviewer": suggestion.approved_by,
                        }
                    )
            else:
                rejections.append(
                    {
                        "concept_id": suggestion.concept_id,
                        "reason": "unsupported_proposal",
                        "reviewer": suggestion.approved_by,
                    }
                )
        return {"overrides": overrides, "rejections": rejections}

    def _build_strata(
        self,
        concepts: Sequence[ConceptFrameRecord],
        facet_combinations: Sequence[Mapping[str, str]],
        constraints: ConstraintConfig,
        policy: PolicyConstraint,
        fan_out: Mapping[str, int],
        difficulty_overrides: Dict[str, List[str]],
    ) -> Tuple[List[StratumAllocationInput], List[CoveragePlanRow]]:
        """Materialise concept × facet strata and capture provenance for allocation."""

        inputs: List[StratumAllocationInput] = []
        rows: List[CoveragePlanRow] = []
        overrides = difficulty_overrides.get("overrides", {})
        seen_dedup: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], str] = {}
        for concept in concepts:
            difficulty = overrides.get(concept.concept_id) or self._infer_difficulty(concept, fan_out)
            risk_tier = self._infer_risk(concept)
            branch = concept.top_branch()
            policy_flags = list(concept.policy_tags)
            for combo in facet_combinations:
                block_reason = self._combo_block_reason(combo, constraints, policy)
                if block_reason:
                    combo_key = tuple(sorted(combo.items()))
                    if combo_key not in self._blocked_combinations_seen:
                        self._blocked_combinations_seen.add(combo_key)
                        self._blocked_combinations_log.append(
                            {
                                "combination": dict(combo),
                                "reason": block_reason,
                            }
                        )
                    continue
                stratum_id = self._build_stratum_id(concept.concept_id, combo)
                dedup_key = (concept.concept_id, tuple(sorted(combo.items())))
                primary_id = seen_dedup.setdefault(dedup_key, stratum_id)
                is_deduplicated = primary_id != stratum_id
                size_weight = max(1, fan_out.get(concept.concept_id, 0) + 1)
                cost_weight = self._lookup_weight(constraints.cost_weights, concept, branch)
                risk_weight = self._lookup_weight(constraints.risk_weights, concept, branch)
                variance = constraints.variance_estimates.get(concept.concept_id)
                observed = constraints.observed_prevalence.get(concept.concept_id)
                minimum = int(concept.domain_attributes.get("minimum_quota", 0))
                maximum = concept.domain_attributes.get("maximum_quota")
                inputs.append(
                    StratumAllocationInput(
                        stratum_id=stratum_id,
                        branch_id=branch,
                        concept_id=concept.concept_id,
                        size_weight=size_weight,
                        variance=variance,
                        cost_weight=cost_weight,
                        risk_weight=risk_weight,
                        minimum=minimum,
                        maximum=maximum,
                        policy_flags=tuple(policy_flags),
                        observed_prevalence=observed,
                    )
                )
                normalized_combo = tuple(sorted(combo.items()))
                coverage_certificate = self._coverage_certificates.get(normalized_combo, ())
                provenance = {
                    "snapshot_id": constraints.concept_snapshot_id,
                    "prevalence_snapshot_id": constraints.prevalence_snapshot_id,
                    "deduplication_group": list(dedup_key[1]),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "coverage_certificate": [list(pair) for pair in coverage_certificate],
                    "deduplicated": is_deduplicated,
                }
                rows.append(
                    CoveragePlanRow(
                        concept_id=concept.concept_id,
                        concept_source=self.config.concept_source,
                        path_to_root=concept.path_to_root,
                        depth=concept.depth,
                        preferred_label=concept.preferred_label,
                        localized_label=concept.domain_attributes.get("localized_label"),
                        branch=branch,
                        depth_band=self._depth_band(concept.depth),
                        difficulty=difficulty,
                        facets=dict(combo),
                        planned_quota=0,
                        minimum_quota=minimum,
                        maximum_quota=maximum,
                        allocation_method=constraints.allocation_strategy,
                        rounding_delta=0.0,
                        policy_flags=tuple(policy_flags),
                        risk_tier=risk_tier,
                        cost_weight=cost_weight,
                        provenance=provenance,
                        solver_logs=tuple(),
                    )
                )
        return inputs, rows

    def _merge_allocations(
        self,
        rows: List[CoveragePlanRow],
        allocation: AllocationResult,
        constraints: ConstraintConfig,
    ) -> List[CoveragePlanRow]:
        """Merge allocation outputs back into the serialisable row structure."""

        row_index = {
            row.concept_id + "|" + "|".join(f"{k}={v}" for k, v in sorted(row.facets.items())): row
            for row in rows
        }
        merged: List[CoveragePlanRow] = []
        constraint_slacks = allocation.solver_details.get('constraint_slacks')
        if constraint_slacks:
            solver_logs = tuple(
                f"{name} slack={value}" for name, value in constraint_slacks.items()
            )
        else:
            solver_logs = tuple(allocation.deviations)
        for stratum_id, quota in allocation.rounded.items():
            row = row_index[stratum_id]
            merged.append(
                CoveragePlanRow(
                    concept_id=row.concept_id,
                    concept_source=row.concept_source,
                    path_to_root=row.path_to_root,
                    depth=row.depth,
                    preferred_label=row.preferred_label,
                    localized_label=row.localized_label,
                    branch=row.branch,
                    depth_band=row.depth_band,
                    difficulty=row.difficulty,
                    facets=row.facets,
                    planned_quota=quota,
                    minimum_quota=row.minimum_quota,
                    maximum_quota=row.maximum_quota,
                    allocation_method=allocation.strategy_used,
                    rounding_delta=allocation.rounding_delta[stratum_id],
                    policy_flags=row.policy_flags,
                    risk_tier=row.risk_tier,
                    cost_weight=row.cost_weight,
                    provenance=row.provenance,
                    solver_logs=solver_logs,
                )
            )
        return merged

    def _build_diagnostics(
        self,
        rows: Sequence[CoveragePlanRow],
        original_concepts: Sequence[ConceptFrameRecord],
        quarantine: Sequence[QuarantineRecord],
        constraints: ConstraintConfig,
    ) -> CoveragePlanDiagnostics:
        """Compute coverage health metrics aligned with Module 5 auditing needs."""

        leaf_ids = {concept.concept_id for concept in original_concepts if concept.is_leaf}
        planned_leaf_ids = {
            row.concept_id for row in rows if row.concept_id in leaf_ids and row.planned_quota > 0
        }
        quarantined_ids = {record.concept_id for record in quarantine}
        row_ids = {row.concept_id for row in rows}
        orphaned = [
            concept.concept_id
            for concept in original_concepts
            if concept.concept_id not in row_ids and concept.concept_id not in quarantined_ids
        ]
        total_leaf_count = len(leaf_ids)
        return build_diagnostics(rows, constraints, total_leaf_count, planned_leaf_ids, orphaned)

    def _build_data_dictionary(self) -> Mapping[str, str]:
        return {
            "concept_id": "Stable identifier of the concept",
            "concept_source": "Upstream module that provided the concept",
            "path_to_root": "Ordered list of ancestor concept IDs",
            "depth": "Depth of the concept in the tree",
            "preferred_label": "Primary label for the concept",
            "localized_label": "Localized label where available",
            "branch": "Top-level branch identifier",
            "depth_band": "Banded depth bucket used for coverage",
            "difficulty": "Difficulty band derived from heuristics or overrides",
            "facets": "Facet assignments for the stratum",
            "planned_quota": "Final quota allocated to the stratum",
            "minimum_quota": "Minimum quota requirement for the stratum",
            "maximum_quota": "Maximum quota cap for the stratum",
            "allocation_method": "Selected allocation strategy",
            "rounding_delta": "Difference introduced by deterministic rounding",
            "policy_flags": "Policy tags attached to the stratum",
            "risk_tier": "Risk tier classification",
            "cost_weight": "Relative cost weight used during allocation",
            "provenance": "Provenance metadata including snapshot references",
            "solver_logs": "Messages emitted while enforcing allocation constraints",
        }

    def _combo_block_reason(
        self,
        combo: Mapping[str, str],
        constraints: ConstraintConfig,
        policy: PolicyConstraint,
    ) -> Optional[str]:
        for facet_name, facet_value in combo.items():
            key = f"{facet_name}:{facet_value}"
            if key in policy.jurisdiction_blocks:
                return f"policy_block:{key}"
        blocked = constraints.slos.get("blocked_jurisdictions") if constraints.slos else None
        if blocked:
            for facet_name, facet_value in combo.items():
                key = f"{facet_name}:{facet_value}"
                if key in blocked:
                    return f"slo_block:{key}"
        return None

    def _build_coverage_certificate(
        self,
        combo: Tuple[Tuple[str, str], ...],
        strength: int,
    ) -> Tuple[Tuple[Tuple[str, str], ...], ...]:
        target_size = max(1, min(strength, len(combo)))
        return tuple(
            tuple(sorted(subset, key=lambda item: item[0]))
            for subset in combinations(combo, target_size)
        )

    def _lookup_weight(
        self,
        mapping: Mapping[str, float],
        concept: ConceptFrameRecord,
        branch: str,
    ) -> Optional[float]:
        """Retrieve cost/risk weights using concept-specific and branch fallbacks."""

        if concept.concept_id in mapping:
            return mapping[concept.concept_id]
        if branch in mapping:
            return mapping[branch]
        fallback_key = f"branch:{branch}"
        if fallback_key in mapping:
            return mapping[fallback_key]
        return None

    def _infer_difficulty(
        self,
        concept: ConceptFrameRecord,
        fan_out: Mapping[str, int],
    ) -> str:
        """Approximate difficulty using handbook heuristics (depth, breadth, lexical cues)."""
        if concept.domain_attributes.get("difficulty_hint"):
            return str(concept.domain_attributes["difficulty_hint"])
        depth = concept.depth
        label = concept.preferred_label.lower()
        fan_out_count = fan_out.get(concept.concept_id, 0)
        if depth <= 2 and fan_out_count <= 2:
            return "easy"
        if depth <= 4:
            if fan_out_count > 5 or any(token in label for token in ("advanced", "regulation")):
                return "hard"
            return "medium"
        return "hard"

    def _infer_risk(self, concept: ConceptFrameRecord) -> RiskTier:
        """Tag strata with coarse risk tiers for policy dashboards."""
        if "safety-critical" in concept.policy_tags or concept.domain_attributes.get("risk") == "high":
            return RiskTier.HIGH
        if concept.domain_attributes.get("risk") == "medium" or concept.depth >= 4:
            return RiskTier.MEDIUM
        return RiskTier.LOW

    def _depth_band(self, depth: int) -> str:
        """Collapse absolute depth into the standard foundation/core/deep bands."""
        if depth <= 1:
            return "foundation"
        if depth <= 3:
            return "core"
        return "deep"

    def _build_stratum_id(self, concept_id: str, facets: Mapping[str, str]) -> str:
        """Stable identifier for concept × facet combinations used across artefacts."""
        facet_part = "|".join(f"{key}={value}" for key, value in sorted(facets.items()))
        if facet_part:
            return f"{concept_id}|{facet_part}"
        return concept_id
