from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

LLM_SRC = ROOT / "llm-demo" / "src"
if LLM_SRC.exists() and str(LLM_SRC) not in sys.path:
    sys.path.insert(0, str(LLM_SRC))

import pytest  # noqa: E402

from DomainDetermine.readiness.models import SuiteConfig, SuiteThresholds, SuiteType  # noqa: E402

# Disable OTEL export during tests to avoid noisy connection errors when a collector
# is not running. Individual tests can override as needed.
os.environ.setdefault("OTEL_METRICS_EXPORTER", "none")
os.environ.setdefault("OTEL_TRACES_EXPORTER", "none")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("READINESS_ENABLE_OTEL", "0")
os.environ.setdefault("GOVERNANCE_ENABLE_OTEL", "0")

warnings.filterwarnings(
    "ignore",
    message="Importing 'parser.split_arg_string' is deprecated",
    category=DeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    message="ConjunctiveGraph is deprecated, use Dataset instead.",
    category=DeprecationWarning,
)


@pytest.fixture
def mapping_schema_dir(tmp_path: Path) -> Path:
    schemas = tmp_path / "schemas"
    schemas.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": "mapping_decision:v1",
        "name": "mapping_decision",
        "version": "v1",
        "description": "Test schema",
        "schema": {
            "type": "object",
            "properties": {
                "concept_id": {"type": "string"},
                "confidence": {"type": ["number", "string"]},
            },
            "required": ["concept_id"],
        },
    }
    (schemas / "mapping_decision_v1.json").write_text(json.dumps(payload), encoding="utf-8")
    return schemas


@pytest.fixture
def reviews_manifest(tmp_path: Path) -> Path:
    review_manifest = tmp_path / "reviews.json"
    review_manifest.write_text(json.dumps({"local": {"reviewer": "alice", "status": "approved"}}), encoding="utf-8")
    return review_manifest


@pytest.fixture
def suites(tmp_path: Path) -> list[SuiteConfig]:
    failing_script = tmp_path / "fail.sh"
    failing_script.write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
    failing_script.chmod(0o755)
    return [
        SuiteConfig(suite=SuiteType.UNIT, command=["/bin/true"]),
        SuiteConfig(
            suite=SuiteType.INTEGRATION,
            command=[str(failing_script)],
            blocking=True,
            retries=0,
            thresholds=SuiteThresholds(min_success_rate=1.0),
        ),
        SuiteConfig(suite=SuiteType.END_TO_END, command=["/bin/true"]),
    ]
