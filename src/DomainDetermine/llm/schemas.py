"""Schema registry for guided decoding (JSON Schemas and EBNF grammars)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional


@dataclass(frozen=True)
class SchemaRecord:
    name: str
    version: str
    schema: Mapping[str, object]
    description: Optional[str] = None

    @property
    def id(self) -> str:
        return f"{self.name}:{self.version}"


class SchemaRegistry:
    """Filesystem-backed schema registry with versioned records."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def register(self, record: SchemaRecord) -> None:
        path = self._path_for(record.name, record.version)
        payload = {
            "id": record.id,
            "name": record.name,
            "version": record.version,
            "description": record.description,
            "schema": record.schema,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, name: str, version: str) -> Mapping[str, object]:
        return self.load_record(name, version).schema

    def load_record(self, name: str, version: str) -> SchemaRecord:
        path = self._path_for(name, version)
        if not path.exists():
            raise ValueError(f"Schema {name}:{version} not found at {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if "schema" not in data:
            raise ValueError(f"Schema file {path} is missing 'schema' field")
        description = data.get("description")
        schema = data["schema"]
        return SchemaRecord(name=name, version=version, schema=schema, description=description)

    def list_versions(self, name: str) -> Dict[str, Path]:
        versions: Dict[str, Path] = {}
        for file in self._root.glob(f"{name}_*.json"):
            version = file.stem.split("_", 1)[-1]
            versions[version] = file
        return versions

    def _path_for(self, name: str, version: str) -> Path:
        filename = f"{name}_{version}.json"
        return self._root / filename
