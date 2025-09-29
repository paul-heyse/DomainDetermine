"""Data models supporting overlay namespace governance and integration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping, MutableMapping, Optional, Sequence

from DomainDetermine.coverage_planner.models import CoveragePlanRow, RiskTier

ISO_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class OverlayNodeState(str, Enum):
    """Lifecycle states for overlay nodes."""

    CANDIDATE = "candidate"
    APPROVED = "approved"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class EvidenceDocument:
    """Represents a single evidence snippet used to justify a proposal."""

    source_id: str
    text: str
    start_offset: Optional[int]
    end_offset: Optional[int]

    def as_serializable(self) -> Mapping[str, Optional[str | int]]:
        return {
            "source_id": self.source_id,
            "text": self.text,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }


@dataclass(frozen=True)
class EvidencePack:
    """Container for evidence snippets and policy guardrails."""

    documents: Sequence[EvidenceDocument]
    policy_notes: Sequence[str] = field(default_factory=tuple)

    def content_hash(self) -> str:
        """Return a deterministic hash of the evidence pack."""

        payload = [doc.as_serializable() for doc in self.documents]
        data = json.dumps({"documents": payload, "policy_notes": list(self.policy_notes)}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass(frozen=True)
class OverlayProvenance:
    """Provenance metadata needed for reproducibility."""

    kos_snapshot_id: str
    prompt_template_hash: str
    evidence_pack_hash: str
    llm_model_ref: Optional[str]
    created_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> Mapping[str, Optional[str]]:
        return {
            "kos_snapshot_id": self.kos_snapshot_id,
            "prompt_template_hash": self.prompt_template_hash,
            "evidence_pack_hash": self.evidence_pack_hash,
            "llm_model_ref": self.llm_model_ref,
            "created_by": self.created_by,
            "created_at": self.created_at.strftime(ISO_TIME_FORMAT),
        }


@dataclass(frozen=True)
class OverlayNode:
    """Represents a node inside the overlay namespace."""

    overlay_id: str
    base_concept_id: str
    state: OverlayNodeState
    preferred_labels: Mapping[str, str]
    alt_labels: Mapping[str, Sequence[str]]
    short_definition: str
    long_definition: Optional[str]
    examples: Sequence[str]
    difficulty: str
    jurisdiction_tags: Sequence[str]
    evidence_pack: EvidencePack
    provenance: OverlayProvenance
    coverage_plan_links: Sequence[str] = field(default_factory=tuple)
    prompt_hash: Optional[str] = None
    nearest_concept_id: Optional[str] = None

    def with_state(self, state: OverlayNodeState) -> "OverlayNode":
        """Return a copy of the node with an updated state."""

        return OverlayNode(
            overlay_id=self.overlay_id,
            base_concept_id=self.base_concept_id,
            state=state,
            preferred_labels=self.preferred_labels,
            alt_labels=self.alt_labels,
            short_definition=self.short_definition,
            long_definition=self.long_definition,
            examples=self.examples,
            difficulty=self.difficulty,
            jurisdiction_tags=self.jurisdiction_tags,
            evidence_pack=self.evidence_pack,
            provenance=self.provenance,
            coverage_plan_links=self.coverage_plan_links,
            prompt_hash=self.prompt_hash,
            nearest_concept_id=self.nearest_concept_id,
        )

    def to_module1_record(self) -> Mapping[str, object]:
        """Return a representation compatible with Module 1 exports."""

        return {
            "overlay_id": self.overlay_id,
            "base_concept_id": self.base_concept_id,
            "state": self.state.value,
            "preferred_labels": dict(self.preferred_labels),
            "alt_labels": {lang: tuple(labels) for lang, labels in self.alt_labels.items()},
            "short_definition": self.short_definition,
            "long_definition": self.long_definition,
            "examples": tuple(self.examples),
            "difficulty": self.difficulty,
            "jurisdiction_tags": tuple(self.jurisdiction_tags),
            "evidence_pack_hash": self.evidence_pack.content_hash(),
            "provenance": self.provenance.as_dict(),
            "coverage_plan_links": tuple(self.coverage_plan_links),
            "prompt_hash": self.prompt_hash,
            "nearest_concept_id": self.nearest_concept_id,
        }


@dataclass(frozen=True)
class OverlayLifecycleEvent:
    """Records a lifecycle state transition."""

    overlay_id: str
    from_state: OverlayNodeState
    to_state: OverlayNodeState
    reviewer_id: Optional[str]
    rationale: Optional[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> Mapping[str, Optional[str]]:
        return {
            "overlay_id": self.overlay_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "reviewer_id": self.reviewer_id,
            "rationale": self.rationale,
            "timestamp": self.timestamp.strftime(ISO_TIME_FORMAT),
        }


@dataclass(frozen=True)
class OverlayManifestEntry:
    """Entry describing a published overlay node."""

    overlay_id: str
    base_concept_id: str
    kos_snapshot_id: str
    coverage_plan_ids: Sequence[str]
    provenance: Mapping[str, Optional[str]]
    lifecycle_events: Sequence[Mapping[str, Optional[str]]]
    content_hash: str
    governance: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class OverlayManifest:
    """Content-addressed manifest of overlay nodes."""

    version: str
    nodes: Sequence[OverlayManifestEntry]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def content_hash(self) -> str:
        payload = {
            "version": self.version,
            "generated_at": self.generated_at.strftime(ISO_TIME_FORMAT),
            "nodes": [entry.__dict__ for entry in self.nodes],
        }
        data = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass(frozen=True)
class OverlayCoverageDelta:
    """Represents a coverage planner delta produced by overlay publication."""

    overlay_id: str
    coverage_plan_id: str
    concept_id: str
    preferred_label: str
    difficulty: str
    planned_quota: int
    provenance: Mapping[str, Optional[str]]
    risk_tier: RiskTier

    def to_plan_row(self, template: CoveragePlanRow) -> CoveragePlanRow:
        """Project the delta onto a coverage plan row template."""

        return CoveragePlanRow(
            concept_id=self.overlay_id,
            concept_source="overlay",
            path_to_root=template.path_to_root,
            depth=template.depth,
            preferred_label=self.preferred_label,
            localized_label=template.localized_label,
            branch=template.branch,
            depth_band=template.depth_band,
            difficulty=self.difficulty,
            facets=template.facets,
            planned_quota=self.planned_quota,
            minimum_quota=template.minimum_quota,
            maximum_quota=template.maximum_quota,
            allocation_method=template.allocation_method,
            rounding_delta=template.rounding_delta,
            policy_flags=template.policy_flags,
            risk_tier=self.risk_tier,
            cost_weight=template.cost_weight,
            provenance=self.provenance,
            solver_logs=template.solver_logs,
        )


@dataclass(frozen=True)
class PolicyGuardrail:
    """Represents policy restrictions applied to overlay nodes."""

    forbidden_categories: Sequence[str] = field(default_factory=tuple)
    restricted_jurisdictions: Sequence[str] = field(default_factory=tuple)

    def allows(self, topic: str, jurisdiction: Optional[str]) -> bool:
        if topic in self.forbidden_categories:
            return False
        if jurisdiction and jurisdiction in self.restricted_jurisdictions:
            return False
        return True


def serialize_labels(labels: Mapping[str, Sequence[str]]) -> Mapping[str, Sequence[str]]:
    """Return an immutable copy of label mappings."""

    return {lang: tuple(entries) for lang, entries in labels.items()}


def mutable_label_mapping(labels: Optional[Mapping[str, Sequence[str]]] = None) -> MutableMapping[str, list[str]]:
    """Return a mutable mapping copy for label manipulation."""

    mapping: MutableMapping[str, list[str]] = {}
    if not labels:
        return mapping
    for lang, values in labels.items():
        mapping[lang] = list(values)
    return mapping


__all__ = [
    "EvidenceDocument",
    "EvidencePack",
    "OverlayNode",
    "OverlayNodeState",
    "OverlayProvenance",
    "OverlayLifecycleEvent",
    "OverlayManifestEntry",
    "OverlayManifest",
    "OverlayCoverageDelta",
    "PolicyGuardrail",
    "serialize_labels",
    "mutable_label_mapping",
]
