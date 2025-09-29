"""Schema registry for guided decoding (JSON Schemas and EBNF grammars)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping


@dataclass(frozen=True)
class SchemaRecord:
    name: str
    version: str
    schema: Mapping[str, object]


class SchemaRegistry:
    """Simple filesystem-backed schema registry."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def register(self, record: SchemaRecord) -> None:
        path = self._root / f"{record.name}_{record.version}.json"
        path.write_text(json.dumps(record.schema, indent=2), encoding="utf-8")

    def load(self, name: str, version: str) -> Mapping[str, object]:
        path = self._root / f"{name}_{version}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def list_versions(self, name: str) -> Dict[str, Path]:
        return {
            file.stem.split("_")[-1]: file
            for file in self._root.glob(f"{name}_*.json")
        }
