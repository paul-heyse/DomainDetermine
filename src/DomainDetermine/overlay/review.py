"""Reviewer workbench and pilot workflows for overlay publication."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import mean
from typing import Callable, Mapping, Optional, Sequence

from DomainDetermine.overlay.exceptions import InvalidStateTransitionError
from DomainDetermine.overlay.lifecycle import OverlayRegistry
from DomainDetermine.overlay.models import OverlayNode, OverlayNodeState


class ReviewDecision(str, Enum):
    """Possible reviewer outcomes."""

    ACCEPT = "accept"
    REVISE = "revise"
    REJECT = "reject"


@dataclass(frozen=True)
class ReviewerView:
    """Information surfaced to reviewers for quick decision making."""

    overlay_id: str
    summary: str
    evidence_quotes: Sequence[str]
    sibling_labels: Sequence[str]
    nearest_neighbors: Mapping[str, float]


@dataclass(frozen=True)
class ReviewRecord:
    """Stores the outcome of a reviewer action."""

    overlay_id: str
    reviewer_id: str
    decision: ReviewDecision
    rationale: Optional[str]


class ReviewWorkbench:
    """Coordinates reviewer interaction with overlay candidates."""

    def __init__(
        self,
        registry: OverlayRegistry,
        *,
        neighbor_search: Optional[Callable[[OverlayNode], Mapping[str, float]]] = None,
    ) -> None:
        self._registry = registry
        self._neighbor_search = neighbor_search or (lambda node: {})
        self._records: list[ReviewRecord] = []

    def present(self, overlay_id: str, *, sibling_labels: Sequence[str]) -> ReviewerView:
        node = self._registry.get(overlay_id)
        evidence_quotes = [doc.text for doc in node.evidence_pack.documents]
        nearest_neighbors = self._neighbor_search(node)
        summary = node.short_definition or next(iter(node.preferred_labels.values()))
        return ReviewerView(
            overlay_id=overlay_id,
            summary=summary,
            evidence_quotes=tuple(evidence_quotes),
            sibling_labels=tuple(sibling_labels),
            nearest_neighbors=nearest_neighbors,
        )

    def submit_decision(
        self,
        overlay_id: str,
        *,
        reviewer_id: str,
        decision: ReviewDecision,
        rationale: Optional[str] = None,
    ) -> ReviewRecord:
        node = self._registry.get(overlay_id)
        if node.state is not OverlayNodeState.CANDIDATE and decision is ReviewDecision.ACCEPT:
            raise InvalidStateTransitionError("Only candidate nodes can be accepted")
        match decision:
            case ReviewDecision.ACCEPT:
                self._registry.transition(
                    overlay_id,
                    to_state=OverlayNodeState.APPROVED,
                    reviewer_id=reviewer_id,
                    rationale=rationale,
                )
            case ReviewDecision.REVISE:
                self._registry.transition(
                    overlay_id,
                    to_state=OverlayNodeState.CANDIDATE,
                    reviewer_id=reviewer_id,
                    rationale=rationale or "revision_requested",
                )
            case ReviewDecision.REJECT:
                self._registry.transition(
                    overlay_id,
                    to_state=OverlayNodeState.DEPRECATED,
                    reviewer_id=reviewer_id,
                    rationale=rationale or "rejected",
                )
        record = ReviewRecord(overlay_id=overlay_id, reviewer_id=reviewer_id, decision=decision, rationale=rationale)
        self._records.append(record)
        return record

    def decisions(self) -> Sequence[ReviewRecord]:
        return tuple(self._records)


@dataclass(frozen=True)
class PilotConfig:
    """Configuration for pilot annotation validation."""

    sample_size: int
    iaa_threshold: float
    throughput_threshold: float


@dataclass(frozen=True)
class PilotAnnotation:
    """Recorded annotations from a single pilot item."""

    item_id: str
    annotations: Sequence[str]
    durations_seconds: Sequence[float]


@dataclass(frozen=True)
class PilotResult:
    """Aggregated pilot metrics."""

    iaa: float
    average_duration: float
    sample_size: int
    passes: bool


class PilotOrchestrator:
    """Evaluates overlay annotatability before publication."""

    def __init__(self, registry: OverlayRegistry) -> None:
        self._registry = registry

    def run_pilot(
        self,
        overlay_id: str,
        *,
        config: PilotConfig,
        samples: Sequence[PilotAnnotation],
        reviewer_id: str,
        rationale: Optional[str] = None,
    ) -> PilotResult:
        iaa = _compute_percent_agreement(samples)
        average_duration = mean(duration for sample in samples for duration in sample.durations_seconds)
        passes = iaa >= config.iaa_threshold and average_duration <= config.throughput_threshold
        self._registry.get(overlay_id)
        if passes:
            self._registry.transition(
                overlay_id,
                to_state=OverlayNodeState.PUBLISHED,
                reviewer_id=reviewer_id,
                rationale=rationale or "pilot_pass",
            )
        else:
            self._registry.transition(
                overlay_id,
                to_state=OverlayNodeState.CANDIDATE,
                reviewer_id=reviewer_id,
                rationale=rationale or "pilot_fail",
            )
        return PilotResult(
            iaa=iaa,
            average_duration=average_duration,
            sample_size=len(samples),
            passes=passes,
        )


@dataclass(frozen=True)
class SplitOperation:
    """Describes a split of an existing overlay node into children."""

    parent_overlay_id: str
    child_labels: Sequence[str]
    migration_notes: Sequence[str]


@dataclass(frozen=True)
class MergeOperation:
    """Describes merging a deprecated node into a canonical node."""

    deprecated_overlay_ids: Sequence[str]
    canonical_overlay_id: str
    justification: str


@dataclass(frozen=True)
class SynonymOperation:
    """Represents synonym additions pending approval."""

    overlay_id: str
    language: str
    synonym: str


class MigrationPlanner:
    """Produces migration hints for split and merge decisions."""

    def build_split_plan(self, node: OverlayNode, children: Sequence[str]) -> SplitOperation:
        migration_notes = [
            f"Remap mappings referencing '{node.overlay_id}' to child '{child}'"
            for child in children
        ]
        return SplitOperation(parent_overlay_id=node.overlay_id, child_labels=tuple(children), migration_notes=tuple(migration_notes))

    def build_merge_plan(self, canonical: OverlayNode, duplicates: Sequence[OverlayNode]) -> MergeOperation:
        deprecated_ids = [dup.overlay_id for dup in duplicates]
        justification = (
            f"Merge {', '.join(deprecated_ids)} into {canonical.overlay_id} due to semantic equivalence"
        )
        return MergeOperation(
            deprecated_overlay_ids=tuple(deprecated_ids),
            canonical_overlay_id=canonical.overlay_id,
            justification=justification,
        )

    def build_synonym_operations(self, node: OverlayNode, synonyms: Mapping[str, Sequence[str]]) -> Sequence[SynonymOperation]:
        operations: list[SynonymOperation] = []
        for language, entries in synonyms.items():
            for synonym in entries:
                operations.append(
                    SynonymOperation(overlay_id=node.overlay_id, language=language, synonym=synonym)
                )
        return tuple(operations)


def _compute_percent_agreement(samples: Sequence[PilotAnnotation]) -> float:
    total_pairs = 0
    agreements = 0
    for sample in samples:
        annotations = list(sample.annotations)
        for idx, label in enumerate(annotations):
            for other in annotations[idx + 1 :]:
                total_pairs += 1
                if label == other:
                    agreements += 1
    return agreements / total_pairs if total_pairs else 1.0


__all__ = [
    "MigrationPlanner",
    "PilotAnnotation",
    "PilotConfig",
    "PilotOrchestrator",
    "PilotResult",
    "ReviewDecision",
    "ReviewWorkbench",
    "ReviewerView",
]
