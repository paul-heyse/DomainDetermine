"""Eval suite generation package (Module 6).

This package transforms coverage plans into versioned evaluation suites with
deterministic graders, slice manifests, and governance controls.
"""

from .builder import EvalSuiteBuilder, ManifestFactory
from .grader import GraderContract, GraderRegistry
from .metrics import MetricCalculator
from .models import (
    DocumentationPack,
    EvalSuite,
    EvalSuiteManifest,
    InstructionPack,
    ItemSchema,
    MetricSpec,
    PolicyPack,
    RunnerConfig,
    ScenarioDefinition,
    SeedDataset,
    SliceDefinition,
    SliceSamplingConfig,
)
from .pipeline import EvalSuitePipeline
from .planning import ScenarioRule, SuiteComposer
from .registry import MetricRegistry, SliceRegistry
from .reporting import ReportGenerator, Scorecard
from .runner import EvalSuiteRunner
from .sampler import SliceSampler, default_sampler
from .storage import EvalSuiteStorage
from .telemetry import EvalSuiteTelemetry

__all__ = [
    "DocumentationPack",
    "EvalSuite",
    "EvalSuiteBuilder",
    "EvalSuiteManifest",
    "EvalSuitePipeline",
    "EvalSuiteRunner",
    "EvalSuiteStorage",
    "EvalSuiteTelemetry",
    "GraderContract",
    "GraderRegistry",
    "InstructionPack",
    "ItemSchema",
    "ManifestFactory",
    "MetricCalculator",
    "MetricRegistry",
    "MetricSpec",
    "PolicyPack",
    "ReportGenerator",
    "RunnerConfig",
    "ScenarioDefinition",
    "ScenarioRule",
    "Scorecard",
    "SeedDataset",
    "SliceDefinition",
    "SliceRegistry",
    "SliceSampler",
    "SliceSamplingConfig",
    "SuiteComposer",
    "default_sampler",
]

