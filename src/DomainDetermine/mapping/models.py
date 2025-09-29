"""Core data models for the mapping and crosswalk pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Iterable, Mapping, Optional, Sequence


class CandidateSource(Enum):
    """Enumerates candidate generation methods."""

    LEXICAL = "lexical"
    SEMANTIC = "semantic"
    GRAPH = "graph"
    CROSS_ENCODER = "cross_encoder"


class DecisionMethod(Enum):
    """Enumerates pipeline decision mechanisms."""

    HEURISTIC = "heuristic"
    LLM = "llm"
    HUMAN = "human"


@dataclass(slots=True)
class ConceptEntry:
    """Represents a concept record from Module 1."""

    concept_id: str
    pref_label: str
    alt_labels: Sequence[str] = field(default_factory=tuple)
    definition: Optional[str] = None
    scope_note: Optional[str] = None
    language: Optional[str] = None
    broader: Sequence[str] = field(default_factory=tuple)
    narrower: Sequence[str] = field(default_factory=tuple)
    mappings: Mapping[str, Sequence[str]] = field(default_factory=dict)
    is_deprecated: bool = False


@dataclass(slots=True)
class MappingContext:
    """Optional contextual metadata from Module 2."""

    domain: Optional[str] = None
    jurisdiction: Optional[str] = None
    language: Optional[str] = None
    coverage_plan_slice_id: Optional[str] = None
    facets: Mapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class MappingItem:
    """A user supplied mapping request."""

    source_text: str
    context: MappingContext = field(default_factory=MappingContext)
    offset: Optional[tuple[int, int]] = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class Candidate:
    """A candidate concept produced during generation."""

    concept_id: str
    label: str
    source: CandidateSource
    score: float
    evidence: Optional[str] = None
    language: Optional[str] = None


@dataclass(slots=True)
class CandidateLogEntry:
    """Stores ranked candidate information for auditability."""

    mapping_item: MappingItem
    candidates: Sequence[Candidate]
    final_concept_id: Optional[str]
    decision_method: DecisionMethod
    human_notes: Optional[str] = None


@dataclass(slots=True)
class MappingRecord:
    """Represents a persisted mapping decision."""

    mapping_item: MappingItem
    concept_id: str
    confidence: float
    decision_method: DecisionMethod
    evidence_quotes: Sequence[str]
    method_metadata: Mapping[str, str]
    kos_snapshot_id: str
    coverage_plan_id: Optional[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    llm_model_ref: Optional[str] = None


@dataclass(slots=True)
class CrosswalkProposal:
    """Represents a pending cross-scheme mapping assertion."""

    source_concept_id: str
    target_scheme: str
    target_concept_id: str
    relation: str
    lexical_score: float
    semantic_score: float
    llm_rationale: Optional[str]
    evidence_quotes: Sequence[str]
    proposer: DecisionMethod
    kos_snapshot_id: str
    status: str = "pending"
    reviewer: Optional[str] = None
    reviewed_at: Optional[datetime] = None


@dataclass(slots=True)
class MappingBatchResult:
    """Aggregated outcome of processing a batch of mapping items."""

    records: Sequence[MappingRecord]
    candidate_logs: Sequence[CandidateLogEntry]
    crosswalk_proposals: Sequence[CrosswalkProposal]
    metrics: Mapping[str, float]


def ensure_iterable(value: Optional[Iterable[str]]) -> Sequence[str]:
    """Return an immutable sequence from the provided iterable."""

    if value is None:
        return tuple()
    if isinstance(value, tuple):
        return value
    return tuple(value)

