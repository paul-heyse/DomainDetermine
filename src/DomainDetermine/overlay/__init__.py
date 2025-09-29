"""Overlay module entry-point exporting primary interfaces."""

from DomainDetermine.overlay.candidate import (
    CandidatePipeline,
    CorpusCandidateMiner,
    CoverageGap,
    OntologyHoleDetector,
    StructuredCandidate,
)
from DomainDetermine.overlay.lifecycle import OverlayRegistry
from DomainDetermine.overlay.models import (
    EvidenceDocument,
    EvidencePack,
    OverlayManifest,
    OverlayNode,
    OverlayNodeState,
    OverlayProvenance,
)
from DomainDetermine.overlay.observability import (
    InternationalizationValidator,
    OverlayLogger,
    RiskControlConfig,
    RiskControlEngine,
)
from DomainDetermine.overlay.quality import OverlayQualityGateConfig
from DomainDetermine.overlay.review import (
    PilotAnnotation,
    PilotConfig,
    PilotOrchestrator,
    ReviewDecision,
    ReviewWorkbench,
)

__all__ = [
    "CandidatePipeline",
    "CorpusCandidateMiner",
    "CoverageGap",
    "EvidenceDocument",
    "EvidencePack",
    "InternationalizationValidator",
    "OntologyHoleDetector",
    "OverlayLogger",
    "OverlayManifest",
    "OverlayNode",
    "OverlayNodeState",
    "OverlayProvenance",
    "OverlayQualityGateConfig",
    "OverlayRegistry",
    "PilotAnnotation",
    "PilotConfig",
    "PilotOrchestrator",
    "ReviewDecision",
    "ReviewWorkbench",
    "RiskControlConfig",
    "RiskControlEngine",
    "StructuredCandidate",
]
