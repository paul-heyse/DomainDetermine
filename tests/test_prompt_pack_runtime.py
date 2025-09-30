from __future__ import annotations

import json
from pathlib import Path

from DomainDetermine.prompt_pack.runtime import PromptRuntimeManager


def write_manifest(tmp_path: Path) -> Path:
    manifest = {
        "version": "2025.09.30",
        "generated_at": "2025-09-30T12:00:00Z",
        "provenance": {
            "module": "module-6",
            "release": "2025.09",
        },
        "templates": [
            {
                "id": "mapping_decision",
                "version": "1.0.0",
                "schema": {"name": "mapping_decision", "version": "v1"},
                "policy_id": "mapping_decision_v1",
                "max_tokens": 256,
                "token_budget": 4096,
            }
        ],
    }
    manifest_path = tmp_path / "runtime_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def write_files(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "mapping_decision_v1.j2").write_text("{{ context_json }}", encoding="utf-8")
    metadata = {
        "template_id": "mapping_decision",
        "version": "1.0.0",
        "schema": "mapping_decision_v1",
        "policy": "mapping_decision_v1",
        "description": "Test template",
    }
    (templates_dir / "mapping_decision_v1.json").write_text(json.dumps(metadata), encoding="utf-8")
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir(parents=True, exist_ok=True)
    (schema_dir / "mapping_decision_v1.schema.json").write_text(json.dumps({"type": "object"}), encoding="utf-8")
    policy_dir = tmp_path / "policies"
    policy_dir.mkdir(parents=True, exist_ok=True)
    policy = {
        "allowed_sources": ["concept_definition"],
        "token_budget": {"prompt": 4096, "completion": 256},
        "citation_policy": {"require_citations": True},
        "filter_terms": [],
    }
    (policy_dir / "mapping_decision_v1.policy.json").write_text(json.dumps(policy), encoding="utf-8")


def test_runtime_manager_summary(tmp_path: Path) -> None:
    write_files(tmp_path)
    write_manifest(tmp_path)
    manager = PromptRuntimeManager(tmp_path)
    summary = manager.summary()
    assert summary["metadata"]["version"] == "2025.09.30"
    templates = summary["templates"]
    assert len(templates) == 1
    entry = templates[0]
    assert entry["id"] == "mapping_decision"
    assert entry["version"] == "1.0.0"
    assert entry["schema_id"] == "mapping_decision:v1"
    assert entry["warmup"] is False
