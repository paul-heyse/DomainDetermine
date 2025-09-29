"""Public API for the mapping module."""

from .candidate_generation import CandidateGenerator
from .crosswalk import CrosswalkProposer
from .decision import LLMDecisionEngine
from .models import (
    Candidate,
    CandidateLogEntry,
    ConceptEntry,
    MappingBatchResult,
    MappingContext,
    MappingItem,
    MappingRecord,
)
from .normalization import TextNormalizer
from .pipeline import MappingPipeline
from .reporting import MappingReport
from .repository import ConceptRepository
from .scoring import CandidateScorer
from .storage import MappingStorage

__all__ = [
    "Candidate",
    "CandidateGenerator",
    "CandidateLogEntry",
    "CandidateScorer",
    "ConceptEntry",
    "ConceptRepository",
    "CrosswalkProposer",
    "LLMDecisionEngine",
    "MappingBatchResult",
    "MappingContext",
    "MappingItem",
    "MappingPipeline",
    "MappingRecord",
    "MappingReport",
    "MappingStorage",
    "TextNormalizer",
]
