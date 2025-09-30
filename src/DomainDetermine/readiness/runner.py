"""CLI entrypoint for running readiness pipeline from CI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from .metrics import MetricsEmitter
from .models import SuiteConfig, SuiteThresholds, SuiteType
from .pipeline import ReadinessPipeline
from .telemetry import configure_otel


def _load_config(path: Path) -> Mapping[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _parse_suite(entry: Mapping[str, Any]) -> SuiteConfig:
    suite = SuiteType(entry["suite"])
    command = list(entry["command"])
    env = entry.get("env", {})
    blocking = bool(entry.get("blocking", True))
    retries = int(entry.get("retries", 0))
    timeout = entry.get("timeout")
    thresholds_cfg = entry.get("thresholds")
    thresholds = None
    if thresholds_cfg:
        thresholds = SuiteThresholds(
            max_duration_seconds=thresholds_cfg.get("max_duration_seconds"),
            max_flake_rate=thresholds_cfg.get("max_flake_rate"),
            min_success_rate=thresholds_cfg.get("min_success_rate", 1.0),
            max_error_budget_burn=thresholds_cfg.get("max_error_budget_burn"),
        )
    description = entry.get("description", "")
    artifacts = tuple(entry.get("artifacts", []))
    return SuiteConfig(
        suite=suite,
        command=command,
        env=env,
        blocking=blocking,
        retries=retries,
        timeout_seconds=timeout,
        thresholds=thresholds,
        description=description,
        artifacts=artifacts,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run readiness pipeline")
    parser.add_argument("--config", required=True, help="Path to readiness config YAML")
    parser.add_argument(
        "--workdir",
        default=".",
        help="Working directory for pipeline (artifacts and logs)",
    )
    parser.add_argument(
        "--scorecards",
        default="readiness_scorecards",
        help="Directory for scorecard artifacts",
    )
    args = parser.parse_args()

    configure_otel()
    config = _load_config(Path(args.config))
    suites = [_parse_suite(entry) for entry in config.get("suites", [])]
    metrics_emitter = MetricsEmitter()
    pipeline = ReadinessPipeline(
        suites,
        workdir=Path(args.workdir),
        metrics_emitter=metrics_emitter,
        scorecard_dir=Path(args.scorecards),
    )
    report = pipeline.run()
    points = metrics_emitter.flush()
    metrics_file = Path(args.workdir) / "readiness_metrics.json"
    metrics_file.write_text(
        json.dumps([{"name": p.name, "value": p.value, "tags": p.tags} for p in points], indent=2),
        encoding="utf-8",
    )
    report_payload = {
        "run_id": report.run_id,
        "overall_passed": report.overall_passed,
        "scorecard": report.scorecard_path,
        "failures": list(report.failures),
    }
    report_file = Path(args.workdir) / "readiness_report.json"
    report_file.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    print(json.dumps(report_payload))
    if not report.overall_passed:
        raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
