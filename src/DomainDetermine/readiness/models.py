"""Data models for readiness testing orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Mapping, Sequence


class SuiteType(str, Enum):
    """Readiness suite categories."""

    UNIT = "unit"
    INTEGRATION = "integration"
    END_TO_END = "end-to-end"
    PERFORMANCE = "performance"
    SECURITY = "security"


@dataclass(frozen=True)
class SuiteConfig:
    """Configuration metadata for an individual suite."""

    suite: SuiteType
    command: Sequence[str]
    env: Mapping[str, str] = field(default_factory=dict)
    blocking: bool = True
    retries: int = 0
    timeout_seconds: int | None = None
    thresholds: "SuiteThresholds | None" = None
    description: str = ""
    artifacts: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class SuiteThresholds:
    """Defines readiness gating thresholds for a suite."""

    max_duration_seconds: float | None = None
    max_flake_rate: float | None = None
    min_success_rate: float | None = 1.0
    max_error_budget_burn: float | None = None


@dataclass(frozen=True)
class ReadinessSuiteResult:
    """Outcome of running a readiness suite."""

    suite: SuiteType
    passed: bool
    started_at: datetime
    finished_at: datetime
    command: Sequence[str]
    attempts: int
    stdout_path: str | None = None
    stderr_path: str | None = None
    metrics: Mapping[str, float] = field(default_factory=dict)
    artifacts: Sequence[str] = field(default_factory=tuple)
    notes: str = ""
    threshold_violations: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReadinessReport:
    """Aggregated readiness results for a run."""

    run_id: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    suites: Sequence[ReadinessSuiteResult] = field(default_factory=tuple)
    overall_passed: bool = False
    coverage_summary: Mapping[str, float] = field(default_factory=dict)
    failures: Sequence[str] = field(default_factory=tuple)

    scorecard_path: str | None = None

    def blocking_failures(self) -> Sequence[ReadinessSuiteResult]:
        return tuple(result for result in self.suites if not result.passed)

