"""Data models for Module 6 evaluation suite generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Optional, Sequence


def hash_payload(payload: Any) -> str:
    """Return a deterministic hash for an arbitrary JSON-serialisable payload."""

    import json

    normalised = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(normalised.encode("utf-8")).hexdigest()


class GraderType(str, Enum):
    """Enumerates grader contract categories."""

    DETERMINISTIC = "deterministic"
    HUMAN_RUBRIC = "human_rubric"
    LLM_JUDGE = "llm_judge"


class SamplingMode(str, Enum):
    """Indicates how slice items are sourced."""

    STATIC = "static"
    SEMI_DYNAMIC = "semi_dynamic"


@dataclass(frozen=True)
class InstructionPack:
    """Instruction pack metadata supplied to the builder."""

    pack_id: str
    version: str
    description: str
    rubric_reference: str
    hash: str
    documentation_link: Optional[str] = None


@dataclass(frozen=True)
class PolicyPack:
    """Policy pack describing behavioural constraints."""

    pack_id: str
    version: str
    description: str
    policy_hash: str
    confidentiality: Optional[str] = None


@dataclass(frozen=True)
class SeedDataset:
    """Optional seed dataset used for calibration or baselining."""

    dataset_id: str
    version: str
    hash: str
    purpose: str


@dataclass(frozen=True)
class MetricSpec:
    """Metric configuration used within a suite."""

    metric_id: str
    name: str
    description: str
    slice_threshold: Optional[float]
    suite_threshold: Optional[float]
    higher_is_better: bool
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def hash(self) -> str:
        payload = {
            "metric_id": self.metric_id,
            "name": self.name,
            "description": self.description,
            "slice_threshold": self.slice_threshold,
            "suite_threshold": self.suite_threshold,
            "higher_is_better": self.higher_is_better,
            "parameters": dict(self.parameters),
        }
        return hash_payload(payload)


@dataclass(frozen=True)
class GraderReference:
    """Reference to a grader implementation and its hashes."""

    grader_id: str
    grader_type: GraderType
    code_hash: str
    config_hash: str
    description: str
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SliceSamplingConfig:
    """Sampling configuration guaranteeing reproducibility."""

    mode: SamplingMode
    seed: Optional[int]
    frame_id: Optional[str] = None
    inclusion_list: Sequence[str] = field(default_factory=tuple)
    exclusion_list: Sequence[str] = field(default_factory=tuple)

    def hash(self) -> str:
        payload = {
            "mode": self.mode,
            "seed": self.seed,
            "frame_id": self.frame_id,
            "inclusion_list": list(self.inclusion_list),
            "exclusion_list": list(self.exclusion_list),
        }
        return hash_payload(payload)


@dataclass(frozen=True)
class SliceDefinition:
    """A slice aligned to a coverage plan row."""

    slice_id: str
    scenario_id: str
    concept_id: str
    facets: Mapping[str, str]
    difficulty: str
    policy_flags: Sequence[str]
    quota: int
    allocation_method: str
    coverage_certificate: Optional[str]
    provenance_hash: str
    sampling: SliceSamplingConfig
    static_item_hash: Optional[str] = None

    def hash(self) -> str:
        payload = {
            "slice_id": self.slice_id,
            "scenario_id": self.scenario_id,
            "concept_id": self.concept_id,
            "facets": dict(self.facets),
            "difficulty": self.difficulty,
            "policy_flags": list(self.policy_flags),
            "quota": self.quota,
            "allocation_method": self.allocation_method,
            "coverage_certificate": self.coverage_certificate,
            "provenance_hash": self.provenance_hash,
            "sampling_hash": self.sampling.hash(),
            "static_item_hash": self.static_item_hash,
        }
        return hash_payload(payload)


@dataclass(frozen=True)
class ItemSchema:
    """Schema definition for items within a scenario."""

    schema_id: str
    task_type: str
    input_format: Mapping[str, Any]
    output_format: Mapping[str, Any]
    evaluation_notes: Sequence[str] = field(default_factory=tuple)

    def hash(self) -> str:
        payload = {
            "schema_id": self.schema_id,
            "task_type": self.task_type,
            "input_format": self.input_format,
            "output_format": self.output_format,
            "evaluation_notes": list(self.evaluation_notes),
        }
        return hash_payload(payload)


@dataclass(frozen=True)
class ScenarioDefinition:
    """Scenario grouping slices and graders."""

    scenario_id: str
    description: str
    test_type: str
    slice_ids: Sequence[str]
    grader_ids: Sequence[str]
    metric_ids: Sequence[str]
    item_schema_id: str


@dataclass(frozen=True)
class RunnerConfig:
    """Configuration for executing an evaluation suite."""

    provider_adapters: Sequence[str]
    cache_enabled: bool
    cache_scope: str
    max_concurrency: int
    retry_limit: int
    timeout_seconds: int
    random_seeds: Mapping[str, int]
    sandbox_policy: Mapping[str, Any]

    def hash(self) -> str:
        payload = {
            "provider_adapters": list(self.provider_adapters),
            "cache_enabled": self.cache_enabled,
            "cache_scope": self.cache_scope,
            "max_concurrency": self.max_concurrency,
            "retry_limit": self.retry_limit,
            "timeout_seconds": self.timeout_seconds,
            "random_seeds": dict(self.random_seeds),
            "sandbox_policy": self.sandbox_policy,
        }
        return hash_payload(payload)


@dataclass(frozen=True)
class DocumentationPack:
    """Human-readable documentation bundle accompanying the suite."""

    summary: str
    methodology: str
    slice_notes: Sequence[str]
    limitations: Sequence[str]
    license_notices: Sequence[str]

    def hash(self) -> str:
        payload = {
            "summary": self.summary,
            "methodology": self.methodology,
            "slice_notes": list(self.slice_notes),
            "limitations": list(self.limitations),
            "license_notices": list(self.license_notices),
        }
        return hash_payload(payload)


@dataclass(frozen=True)
class EvalSuiteManifest:
    """Machine-readable manifest describing a suite."""

    suite_id: str
    suite_version: str
    coverage_plan_version: str
    coverage_plan_snapshot_id: Optional[str]
    instruction_pack_id: str
    policy_pack_id: str
    slice_hashes: Mapping[str, str]
    item_schema_hashes: Mapping[str, str]
    grader_hashes: Mapping[str, str]
    metric_hashes: Mapping[str, str]
    runner_hash: str
    documentation_hash: str
    seed_dataset_hashes: Mapping[str, str]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def checksum(self) -> str:
        payload = {
            "suite_id": self.suite_id,
            "suite_version": self.suite_version,
            "coverage_plan_version": self.coverage_plan_version,
            "slice_hashes": dict(self.slice_hashes),
            "item_schema_hashes": dict(self.item_schema_hashes),
            "grader_hashes": dict(self.grader_hashes),
            "metric_hashes": dict(self.metric_hashes),
            "runner_hash": self.runner_hash,
            "documentation_hash": self.documentation_hash,
            "seed_dataset_hashes": dict(self.seed_dataset_hashes),
        }
        return hash_payload(payload)


@dataclass(frozen=True)
class EvalSuite:
    """Complete evaluation suite artifact."""

    manifest: EvalSuiteManifest
    slices: Mapping[str, SliceDefinition]
    scenarios: Mapping[str, ScenarioDefinition]
    graders: Mapping[str, GraderReference]
    metrics: Mapping[str, MetricSpec]
    item_schemas: Mapping[str, ItemSchema]
    runner: RunnerConfig
    documentation: DocumentationPack
    seed_datasets: Sequence[SeedDataset]


