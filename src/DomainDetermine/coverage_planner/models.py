"""Data models that support coverage planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


class RiskTier(str, Enum):
    """Enumerates the coarse risk categories for strata."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ConceptFrameRecord:
    """Normalized concept metadata coming from Module 1."""

    concept_id: str
    preferred_label: str
    path_to_root: Tuple[str, ...]
    depth: int
    is_leaf: bool
    is_deprecated: bool
    domain_attributes: Mapping[str, Any] = field(default_factory=dict)
    policy_tags: Sequence[str] = field(default_factory=tuple)
    ancestor_paths: Sequence[Tuple[str, ...]] = field(default_factory=tuple)

    def top_branch(self) -> str:
        """Return the highest-level branch identifier for fairness metrics."""

        if not self.path_to_root:
            return self.concept_id
        return self.path_to_root[1] if len(self.path_to_root) > 1 else self.path_to_root[0]


@dataclass(frozen=True)
class FacetDefinition:
    """Configuration for a single facet axis."""

    name: str
    values: Sequence[str]
    required: bool = True
    default: Optional[str] = None

    def validate(self) -> None:
        if not self.values:
            msg = f"Facet '{self.name}' must define at least one value"
            raise ValueError(msg)
        if self.default and self.default not in self.values:
            msg = f"Default value '{self.default}' is not in the value list for facet '{self.name}'"
            raise ValueError(msg)


@dataclass
class FacetConfig:
    """Complete facet configuration for a plan."""

    facets: Sequence[FacetDefinition]
    invalid_combinations: Sequence[Sequence[Tuple[str, str]]] = field(default_factory=tuple)
    max_combinations: int = 500
    coverage_strength: int = 2

    def as_mapping(self) -> Mapping[str, Sequence[str]]:
        """Return a name → values mapping for convenience."""

        return {facet.name: tuple(facet.values) for facet in self.facets}


@dataclass
class PolicyConstraint:
    """Risk and policy controls applied during planning."""

    forbidden_concepts: Sequence[str] = field(default_factory=tuple)
    forbidden_policy_tags: Sequence[str] = field(default_factory=tuple)
    jurisdiction_blocks: Sequence[str] = field(default_factory=tuple)
    audit_requirements: Mapping[str, str] = field(default_factory=dict)

    def concept_is_forbidden(self, concept: ConceptFrameRecord) -> bool:
        if concept.concept_id in self.forbidden_concepts:
            return True
        if not self.forbidden_policy_tags:
            return False
        return any(tag in self.forbidden_policy_tags for tag in concept.policy_tags)


@dataclass
class ConstraintConfig:
    """Allocation constraints supplied by business stakeholders."""

    total_items: int
    branch_minimums: Mapping[str, int] = field(default_factory=dict)
    branch_maximums: Mapping[str, int] = field(default_factory=dict)
    fairness_floor: Optional[float] = None
    fairness_ceiling: Optional[float] = None
    cost_weights: Mapping[str, float] = field(default_factory=dict)
    risk_weights: Mapping[str, float] = field(default_factory=dict)
    slos: Mapping[str, float] = field(default_factory=dict)
    observed_prevalence: Mapping[str, float] = field(default_factory=dict)
    variance_estimates: Mapping[str, float] = field(default_factory=dict)
    mixing_parameter: float = 0.0
    allocation_strategy: str = "uniform"
    fallback_strategy: str = "uniform"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    concept_snapshot_id: Optional[str] = None
    prevalence_snapshot_id: Optional[str] = None
    allocation_version: str = "v1"

    def validate(self) -> None:
        if self.total_items <= 0:
            raise ValueError("total_items must be positive")
        if not 0.0 <= self.mixing_parameter <= 1.0:
            raise ValueError("mixing_parameter must be between 0.0 and 1.0 inclusive")
        if self.fairness_floor and self.fairness_floor < 0.0:
            raise ValueError("fairness_floor cannot be negative")
        if self.fairness_ceiling and self.fairness_ceiling <= 0.0:
            raise ValueError("fairness_ceiling must be positive")
        if self.allocation_strategy == "cost_constrained" and self.fallback_strategy == "cost_constrained":
            raise ValueError("fallback_strategy must differ from cost_constrained when LP fallback is required")


@dataclass(frozen=True)
class LlmSuggestion:
    """An optional LLM-generated refinement subject to human approval."""

    concept_id: str
    proposal_type: str
    payload: Mapping[str, Any]
    citations: Sequence[str]
    approved_by: Optional[str]
    approved_at: Optional[datetime]

    def is_approved(self) -> bool:
        return bool(self.approved_by and self.approved_at)


@dataclass(frozen=True)
class QuarantineRecord:
    """Represents a concept or stratum removed for policy reasons."""

    concept_id: str
    reason: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SolverFailureManifest:
    """Details emitted when LP solver fails and a fallback is used."""

    strategy: str
    reason: str
    violated_constraints: Sequence[str] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AllocationMetadata:
    """Metadata captured for each allocation run."""

    strategy: str
    pre_round_totals: Mapping[str, float]
    post_round_totals: Mapping[str, int]
    rounding_deltas: Mapping[str, float]
    parameters: Mapping[str, Any]
    solver_details: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class AllocationReport:
    """Structured description of allocation behavior."""

    summary: str
    fairness_notes: Sequence[str]
    deviations: Sequence[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "fairness_notes": list(self.fairness_notes),
            "deviations": list(self.deviations),
        }


@dataclass
class CoveragePlanRow:
    """Single row of the coverage plan table."""

    concept_id: str
    concept_source: str
    path_to_root: Tuple[str, ...]
    depth: int
    preferred_label: str
    localized_label: Optional[str]
    branch: str
    depth_band: str
    difficulty: str
    facets: Mapping[str, str]
    planned_quota: int
    minimum_quota: int
    maximum_quota: Optional[int]
    allocation_method: str
    rounding_delta: float
    policy_flags: Sequence[str]
    risk_tier: RiskTier
    cost_weight: Optional[float]
    provenance: Mapping[str, Any]
    solver_logs: Sequence[str] = field(default_factory=tuple)


@dataclass
class CoveragePlanDiagnostics:
    """Diagnostics calculated for plan auditing."""

    quotas_by_branch: Mapping[str, int]
    quotas_by_depth_band: Mapping[str, int]
    quotas_by_facet: Mapping[str, Mapping[str, int]]
    leaf_coverage_ratio: float
    entropy: float
    gini_coefficient: float
    red_flags: Sequence[str]


@dataclass
class CoveragePlanVersion:
    """Version metadata for a coverage plan."""

    version: str
    concept_snapshot_id: Optional[str]
    created_at: datetime
    author: str
    reviewer: Optional[str]
    changelog: Sequence[str]


@dataclass
class CoveragePlan:
    """Aggregate output of the coverage planner."""

    rows: Sequence[CoveragePlanRow]
    metadata: AllocationMetadata
    diagnostics: CoveragePlanDiagnostics
    data_dictionary: Mapping[str, str]
    allocation_report: AllocationReport
    quarantine: Sequence[QuarantineRecord]
    version: CoveragePlanVersion
    solver_failure: Optional[SolverFailureManifest] = None
    what_if_runs: Sequence[AllocationMetadata] = field(default_factory=tuple)
    llm_suggestions: Sequence[LlmSuggestion] = field(default_factory=tuple)

    def total_quota(self) -> int:
        return sum(row.planned_quota for row in self.rows)

    def to_dicts(self) -> Sequence[Dict[str, Any]]:
        """Return plan rows as serializable dictionaries."""

        payload = []
        for row in self.rows:
            payload.append(
                {
                    "concept_id": row.concept_id,
                    "concept_source": row.concept_source,
                    "path_to_root": list(row.path_to_root),
                    "depth": row.depth,
                    "preferred_label": row.preferred_label,
                    "localized_label": row.localized_label,
                    "branch": row.branch,
                    "depth_band": row.depth_band,
                    "difficulty": row.difficulty,
                    "facets": dict(row.facets),
                    "planned_quota": row.planned_quota,
                    "minimum_quota": row.minimum_quota,
                    "maximum_quota": row.maximum_quota,
                    "allocation_method": row.allocation_method,
                    "rounding_delta": row.rounding_delta,
                    "policy_flags": list(row.policy_flags),
                    "risk_tier": row.risk_tier.value,
                    "cost_weight": row.cost_weight,
                    "provenance": dict(row.provenance),
                    "solver_logs": list(row.solver_logs),
                }
            )
        return payload
