from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Optional

import pytest

from DomainDetermine.readiness.models import (
    ReadinessReport,
    SuiteConfig,
    SuiteThresholds,
    SuiteType,
)
from DomainDetermine.readiness.pipeline import ReadinessPipeline


@pytest.fixture
def suites(tmp_path: Path) -> list[SuiteConfig]:
    script = tmp_path / "failing.sh"
    script.write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
    script.chmod(0o755)
    return [
        SuiteConfig(suite=SuiteType.UNIT, command=["/bin/true"]),
        SuiteConfig(suite=SuiteType.INTEGRATION, command=[str(script)], blocking=True),
    ]


class DummyTelemetry:
    def __init__(self) -> None:
        self._latest: dict[str, object] | None = None

    def record_readiness_summary(
        self,
        *,
        generated_at,
        overall_passed: bool,
        failures: list[str],
        coverage: Mapping[str, float],
    ) -> None:
        self._latest = {
            "generated_at": generated_at,
            "overall_passed": overall_passed,
            "failures": failures,
            "coverage": coverage,
        }

    def latest_readiness(self) -> Optional[dict[str, object]]:
        return self._latest


@pytest.fixture
def telemetry() -> DummyTelemetry:
    return DummyTelemetry()


def test_pipeline_runs_until_blocking_failure(tmp_path: Path, suites: list[SuiteConfig], telemetry: DummyTelemetry) -> None:
    runner = ReadinessPipeline(suites, workdir=tmp_path, telemetry=telemetry)
    report = runner.run()
    assert isinstance(report, ReadinessReport)
    assert report.failures == ("integration",)
    summaries = json.loads(Path(report.scorecard_path).read_text())
    assert summaries["suites"][0]["suite"] == "unit"
    telemetry = runner._telemetry
    summary = telemetry.latest_readiness()
    assert summary is not None
    assert summary["overall_passed"] is False
    assert "integration" in summary["failures"]


def test_pipeline_retries_non_blocking_suite(tmp_path: Path) -> None:
    script = tmp_path / "flaky.sh"
    script.write_text("#!/bin/bash\nif [ ! -f success ]; then touch success; exit 1; fi\n", encoding="utf-8")
    script.chmod(0o755)
    pipeline = ReadinessPipeline(
        [
            SuiteConfig(suite=SuiteType.UNIT, command=["/bin/true"]),
            SuiteConfig(
                suite=SuiteType.INTEGRATION,
                command=[str(script)],
                retries=1,
                blocking=False,
                thresholds=SuiteThresholds(min_success_rate=0.9, max_flake_rate=0.5),
            ),
            SuiteConfig(suite=SuiteType.END_TO_END, command=["/bin/true"]),
        ],
        workdir=tmp_path,
    )
    report = pipeline.run()
    assert report.overall_passed
    integration = next(result for result in report.suites if result.suite is SuiteType.INTEGRATION)
    assert integration.attempts == 2
    assert integration.passed
    assert not integration.threshold_violations


def test_pipeline_requires_suites() -> None:
    with pytest.raises(ValueError, match="At least one readiness suite configuration is required"):
        ReadinessPipeline([])

