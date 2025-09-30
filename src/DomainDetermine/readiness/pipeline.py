"""Orchestrates readiness test execution."""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from DomainDetermine.governance.telemetry import GovernanceTelemetry

from .metrics import MetricsEmitter
from .models import ReadinessReport, ReadinessSuiteResult, SuiteConfig


@contextmanager
def dummy_context_manager(*args, **kwargs):  # pragma: no cover - helper
    yield None

try:  # Optional OpenTelemetry tracing
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
except Exception:  # pragma: no cover - OTEL optional
    trace = None
    Status = None
    StatusCode = None


class ReadinessPipeline:
    """Runs configured readiness suites and produces reports."""

    def __init__(
        self,
        suites: Iterable[SuiteConfig],
        *,
        workdir: Path | None = None,
        metrics_emitter: MetricsEmitter | None = None,
        scorecard_dir: Path | None = None,
        telemetry: GovernanceTelemetry | None = None,
    ) -> None:
        self._suites = tuple(suites)
        if not self._suites:
            msg = "At least one readiness suite configuration is required"
            raise ValueError(msg)
        self._workdir = workdir or Path.cwd()
        self._metrics = metrics_emitter or MetricsEmitter()
        self._scorecard_dir = scorecard_dir or self._workdir / "readiness_scorecards"
        self._scorecard_dir.mkdir(parents=True, exist_ok=True)
        self._telemetry = telemetry
        enable_tracing = os.environ.get("READINESS_ENABLE_OTEL", "0") == "1"
        self._tracer = (
            trace.get_tracer("domain_determine.readiness")
            if trace and enable_tracing
            else None
        )
        if not self._tracer:
            self._tracer_context = dummy_context_manager
        else:
            self._tracer_context = self._tracer.start_as_current_span

    def run(self) -> ReadinessReport:
        run_id = uuid.uuid4().hex
        results: list[ReadinessSuiteResult] = []
        with self._tracer_context(
            "readiness.run",
            attributes={
                "readiness.run_id": run_id,
                "cicd.pipeline.id": "readiness",
                "cicd.pipeline.run_id": run_id,
            },
        ) if self._tracer else dummy_context_manager() as run_span:
            for config in self._suites:
                result = self._run_suite(config, run_id, parent_span=run_span)
                results.append(result)
                if config.blocking and not result.passed:
                    break
            if run_span:
                run_span.set_attribute("readiness.suites_total", len(results))
        overall_passed = all(result.passed or not self._suite_blocking(result.suite) for result in results)
        failures = [result.suite.value for result in results if not result.passed]
        coverage_summary = {
            "total_suites": float(len(results)),
            "passed": float(sum(result.passed for result in results)),
        }
        scorecard_path = self._write_scorecard(run_id, results, overall_passed)
        if self._telemetry:
            self._telemetry.record_readiness_summary(
                generated_at=datetime.now(timezone.utc),
                overall_passed=overall_passed,
                failures=failures,
                coverage=coverage_summary,
            )
        return ReadinessReport(
            run_id=run_id,
            suites=tuple(results),
            overall_passed=overall_passed,
            coverage_summary=coverage_summary,
            failures=tuple(failures),
            scorecard_path=scorecard_path,
        )

    def _suite_blocking(self, suite) -> bool:
        for config in self._suites:
            if config.suite == suite:
                return config.blocking
        return True

    def _run_suite(self, config: SuiteConfig, run_id: str, parent_span=None) -> ReadinessSuiteResult:
        start = datetime.now(timezone.utc)
        attempts = 0
        passed = False
        stdout_path = None
        stderr_path = None
        artifacts: list[str] = []
        last_error = ""
        with self._tracer_context(
            "readiness.suite",
            attributes={
                "readiness.suite": config.suite.value,
                "cicd.stage.name": config.suite.value,
                "readiness.blocking": config.blocking,
            },
        ) if self._tracer else dummy_context_manager() as span:
            while attempts <= config.retries and not passed:
                attempts += 1
                stdout_path, stderr_path = self._log_paths(run_id, config.suite.value, attempts)
                proc_env = os.environ.copy()
                proc_env.update(config.env)
                with open(stdout_path, "w", encoding="utf-8") as stdout_file, open(
                    stderr_path,
                    "w",
                    encoding="utf-8",
                ) as stderr_file:
                    try:
                        subprocess.run(
                            config.command,
                            cwd=self._workdir,
                            env=proc_env,
                            stdout=stdout_file,
                            stderr=stderr_file,
                            check=True,
                            timeout=config.timeout_seconds,
                        )
                    except subprocess.CalledProcessError as exc:  # pragma: no cover - subprocess error handling
                        last_error = str(exc)
                        continue
                    except subprocess.TimeoutExpired as exc:  # pragma: no cover - subprocess timeout handling
                        last_error = f"timeout: {exc.timeout}s"
                        continue
                    passed = True
        finished = datetime.now(timezone.utc)
        metrics = {
            "duration_seconds": (finished - start).total_seconds(),
            "attempts": float(attempts),
        }
        notes = last_error if not passed else ""
        artifacts.extend(filter(None, (stdout_path, stderr_path)))
        threshold_violations = self._evaluate_thresholds(config, metrics)
        if threshold_violations:
            passed = False
        self._emit_metrics(config, metrics, passed)
        if span:
            span.set_attribute("readiness.duration_seconds", metrics["duration_seconds"])
            span.set_attribute("readiness.attempts", attempts)
            span.set_attribute("readiness.threshold_violations", len(threshold_violations))
            if passed:
                span.set_status(Status(StatusCode.OK))
            else:
                span.set_status(Status(StatusCode.ERROR, description=notes))
        return ReadinessSuiteResult(
            suite=config.suite,
            passed=passed,
            started_at=start,
            finished_at=finished,
            command=config.command,
            attempts=attempts,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            metrics=metrics,
            artifacts=tuple(artifacts),
            notes=notes,
            threshold_violations=tuple(threshold_violations),
        )

    def _log_paths(self, run_id: str, suite_name: str, attempt: int) -> tuple[str, str]:
        base = self._workdir / "readiness_logs" / run_id / suite_name
        base.mkdir(parents=True, exist_ok=True)
        stdout = base / f"attempt_{attempt}.out"
        stderr = base / f"attempt_{attempt}.err"
        return str(stdout), str(stderr)

    def _evaluate_thresholds(self, config: SuiteConfig, metrics: Mapping[str, float]) -> list[str]:
        violations: list[str] = []
        thresholds = config.thresholds
        if not thresholds:
            return violations
        duration = metrics.get("duration_seconds")
        if thresholds.max_duration_seconds is not None and duration is not None:
            if duration > thresholds.max_duration_seconds:
                violations.append(
                    f"duration {duration:.2f}s > max {thresholds.max_duration_seconds:.2f}s"
                )
        success_rate = metrics.get("success_rate")
        if thresholds.min_success_rate is not None and success_rate is not None:
            if success_rate < thresholds.min_success_rate:
                violations.append(
                    f"success rate {success_rate:.2f} < min {thresholds.min_success_rate:.2f}"
                )
        flake_rate = metrics.get("flake_rate")
        if thresholds.max_flake_rate is not None and flake_rate is not None:
            if flake_rate > thresholds.max_flake_rate:
                violations.append(
                    f"flake rate {flake_rate:.2f} > max {thresholds.max_flake_rate:.2f}"
                )
        burn = metrics.get("error_budget_burn")
        if thresholds.max_error_budget_burn is not None and burn is not None:
            if burn > thresholds.max_error_budget_burn:
                violations.append(
                    f"error budget burn {burn:.2f} > max {thresholds.max_error_budget_burn:.2f}"
                )
        return violations

    def _emit_metrics(self, config: SuiteConfig, metrics: Mapping[str, float], passed: bool) -> None:
        tags = {
            "suite": config.suite.value,
            "blocking": str(config.blocking).lower(),
            "passed": str(passed).lower(),
        }
        for name, value in metrics.items():
            self._metrics.emit(f"readiness.{name}", value, **tags)
        self._metrics.emit("readiness.passed", 1.0 if passed else 0.0, **tags)

    def _write_scorecard(
        self,
        run_id: str,
        results: Sequence[ReadinessSuiteResult],
        overall_passed: bool,
    ) -> str:
        scorecard = self._scorecard_dir / f"readiness_scorecard_{run_id}.json"
        payload = {
            "run_id": run_id,
            "overall_passed": overall_passed,
            "suites": [
                {
                    "suite": result.suite.value,
                    "passed": result.passed,
                    "duration_seconds": result.metrics.get("duration_seconds"),
                    "attempts": result.attempts,
                    "threshold_violations": list(result.threshold_violations),
                    "artifacts": list(result.artifacts),
                }
                for result in results
            ],
        }
        scorecard.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(scorecard)
