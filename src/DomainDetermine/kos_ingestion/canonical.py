"""Canonical data structures for normalized KOS snapshots."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LabelRecord:
    concept_id: str
    text: str
    language: Optional[str]
    is_preferred: bool
    kind: str  # pref | alt | acronym | misspelling


@dataclass(frozen=True)
class RelationRecord:
    subject_id: str
    predicate: str
    object_id: str


@dataclass(frozen=True)
class MappingRecord:
    subject_id: str
    mapping_type: str
    target_scheme: str
    target_id: str


@dataclass(frozen=True)
class ConceptRecord:
    canonical_id: str
    source_id: str
    source_scheme: str
    preferred_label: Optional[str]
    definition: Optional[str]
    language: Optional[str]
    depth: int
    is_leaf: bool
    is_deprecated: bool
    path_to_root: Tuple[str, ...]
    provenance: Mapping[str, str]


@dataclass
class SnapshotTables:
    concepts: pd.DataFrame
    labels: pd.DataFrame
    relations: pd.DataFrame
    mappings: pd.DataFrame
    paths: pd.DataFrame

    @classmethod
    def from_records(
        cls,
        concepts: Sequence[ConceptRecord],
        labels: Sequence[LabelRecord],
        relations: Sequence[RelationRecord],
        mappings: Sequence[MappingRecord],
    ) -> "SnapshotTables":
        parent_map: Dict[str, set] = defaultdict(set)
        child_map: Dict[str, set] = defaultdict(set)
        for rel in relations:
            if rel.predicate == "broader":
                parent_map[rel.subject_id].add(rel.object_id)
                child_map[rel.object_id].add(rel.subject_id)
            elif rel.predicate == "narrower":
                child_map[rel.subject_id].add(rel.object_id)
                parent_map[rel.object_id].add(rel.subject_id)

        descendant_cache: Dict[str, int] = {}

        def count_descendants(node: str, stack: Optional[set] = None) -> int:
            if node in descendant_cache:
                return descendant_cache[node]
            if stack is None:
                stack = set()
            if node in stack:
                logger.warning("Cycle detected while counting descendants for %s", node)
                descendant_cache[node] = 0
                return 0
            stack.add(node)
            total = 0
            for child in child_map.get(node, set()):
                total += 1 + count_descendants(child, stack)
            stack.remove(node)
            descendant_cache[node] = total
            return total

        concept_rows: List[Dict[str, object]] = []
        for c in concepts:
            descendant_total = count_descendants(c.canonical_id)
            concept_rows.append(
                {
                    "canonical_id": c.canonical_id,
                    "source_id": c.source_id,
                    "source_scheme": c.source_scheme,
                    "preferred_label": c.preferred_label,
                    "definition": c.definition,
                    "language": c.language,
                    "depth": c.depth,
                    "is_leaf": c.is_leaf,
                    "is_deprecated": c.is_deprecated,
                    "path_to_root": list(c.path_to_root),
                    "child_count": len(child_map.get(c.canonical_id, set())),
                    "descendant_count": descendant_total,
                    "provenance": dict(c.provenance),
                }
            )
        labels_rows = [
            {
                "concept_id": label.concept_id,
                "text": label.text,
                "language": label.language,
                "is_preferred": label.is_preferred,
                "kind": label.kind,
            }
            for label in labels
        ]
        relation_rows = [
            {
                "subject_id": r.subject_id,
                "predicate": r.predicate,
                "object_id": r.object_id,
            }
            for r in relations
        ]
        mapping_rows = [
            {
                "subject_id": m.subject_id,
                "mapping_type": m.mapping_type,
                "target_scheme": m.target_scheme,
                "target_id": m.target_id,
            }
            for m in mappings
        ]

        paths_rows: List[Dict[str, object]] = []
        for concept in concepts:
            paths_rows.append(
                {
                    "concept_id": concept.canonical_id,
                    "ancestor_ids": list(concept.path_to_root),
                    "ancestor_count": len(concept.path_to_root),
                    "descendant_count": descendant_cache.get(concept.canonical_id, 0),
                }
            )

        return cls(
            concepts=pd.DataFrame(concept_rows or [{}]).dropna(how="all"),
            labels=pd.DataFrame(labels_rows or [{}]).dropna(how="all"),
            relations=pd.DataFrame(relation_rows or [{}]).dropna(how="all"),
            mappings=pd.DataFrame(mapping_rows or [{}]).dropna(how="all"),
            paths=pd.DataFrame(paths_rows or [{}]).dropna(how="all"),
        )

    def to_parquet(self, directory: Path) -> Dict[str, Path]:
        directory.mkdir(parents=True, exist_ok=True)
        outputs: Dict[str, Path] = {}
        for name, df in (
            ("concepts", self.concepts),
            ("labels", self.labels),
            ("relations", self.relations),
            ("mappings", self.mappings),
            ("paths", self.paths),
        ):
            path = directory / f"{name}.parquet"
            if not df.empty:
                df.to_parquet(path, index=False)
            else:
                empty_df = pd.DataFrame()
                empty_df.to_parquet(path, index=False)
            outputs[name] = path
        return outputs

    def concept_index(self) -> Mapping[str, Mapping[str, object]]:
        return {
            row["canonical_id"]: row.to_dict()
            for _, row in self.concepts.iterrows()
            if "canonical_id" in row
        }

    def table_schemas(self) -> Mapping[str, Dict[str, str]]:
        return {
            name: {column: str(dtype) for column, dtype in df.dtypes.items()}
            for name, df in (
                ("concepts", self.concepts),
                ("labels", self.labels),
                ("relations", self.relations),
                ("mappings", self.mappings),
                ("paths", self.paths),
            )
        }


@dataclass
class SnapshotManifest:
    snapshot_id: str
    created_at: datetime
    sources: Sequence[Mapping[str, str]]
    table_hashes: Mapping[str, str]
    graph_paths: Sequence[str]
    license_notes: Sequence[str]
    validation_report: Mapping[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at.isoformat(),
            "sources": list(self.sources),
            "table_hashes": dict(self.table_hashes),
            "graph_paths": list(self.graph_paths),
            "license_notes": list(self.license_notes),
            "validation_report": dict(self.validation_report),
        }
