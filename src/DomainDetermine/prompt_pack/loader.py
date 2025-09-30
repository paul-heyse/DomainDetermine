"""Loading utilities for prompt pack templates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import jsonschema


@dataclass(frozen=True)
class TemplateRecord:
    """Represents a prompt template and its metadata."""

    template_path: Path
    metadata_path: Path
    schema_path: Path
    policy_path: Path

    def load_template(self) -> str:
        return self.template_path.read_text(encoding="utf-8")

    def load_metadata(self) -> Mapping[str, object]:
        return json.loads(self.metadata_path.read_text(encoding="utf-8"))

    def validate(self, schema: Mapping[str, object]) -> None:
        jsonschema.validate(instance=self.load_metadata(), schema=schema)


class PromptTemplateLoader:
    """Discovers template records from the prompt pack repository."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def discover(self) -> Iterable[TemplateRecord]:
        templates_dir = self._root / "templates"
        for metadata_path in templates_dir.rglob("*.json"):
            template_path = metadata_path.with_suffix(".j2")
            if not template_path.exists():
                continue
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            template_id = metadata.get("template_id")
            schema_id = metadata.get("schema")
            policy_id = metadata.get("policy")
            if not (template_id and schema_id and policy_id):
                continue
            schema_path = self._root / "schemas" / f"{schema_id}.schema.json"
            policy_path = self._root / "policies" / f"{policy_id}.policy.json"
            if not (schema_path.exists() and policy_path.exists()):
                continue
            yield TemplateRecord(
                template_path=template_path,
                metadata_path=metadata_path,
                schema_path=schema_path,
                policy_path=policy_path,
            )
