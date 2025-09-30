"""Validation utilities for KOS snapshots."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import pandas as pd
import pandera.pandas as pa
from rdflib import Graph

from .canonical import SnapshotTables
from .models import ParserOutput, SourceConfig

logger = logging.getLogger(__name__)

try:  # pyshacl is optional at runtime
    from pyshacl import validate as pyshacl_validate
except Exception:  # pragma: no cover - optional dependency
    pyshacl_validate = None

DEFAULT_SHACL_SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

skos:ConceptShape
    a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:property [
        sh:path skos:prefLabel ;
        sh:minCount 1 ;
    ] .
"""


@dataclass
class ValidationResult:
    """Container for validation outputs."""

    shacl: Mapping[str, Any] = field(default_factory=dict)
    tabular: Mapping[str, Any] = field(default_factory=dict)
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shacl": dict(self.shacl),
            "tabular": dict(self.tabular),
            "diagnostics": dict(self.diagnostics),
            "severity": self.severity(),
        }

    def severity(self) -> str:
        if self.shacl.get("status") == "failed" or self.shacl.get("status") == "error":
            return "blocker"
        if self.tabular.get("status") == "failed":
            return "blocker"
        summary = self.diagnostics.get("summary", {})
        significant_diagnostics = any(summary.get(name, 0) > 0 for name in (
            "duplicate_labels",
            "conflicting_mappings",
            "definition_length_flags",
        ))
        if significant_diagnostics:
            return "needs_review"
        return "passed"


class KOSValidator:
    """Runs structural and tabular validations over snapshot outputs."""

    def __init__(
        self,
        *,
        shacl_shapes: Optional[Graph] = None,
        pandera_enabled: bool = True,
    ) -> None:
        self._shapes_graph = shacl_shapes
        self._pandera_enabled = pandera_enabled

    def validate(
        self,
        config: SourceConfig,
        tables: SnapshotTables,
        parser_output: Optional[ParserOutput],
    ) -> ValidationResult:
        """Execute SHACL + tabular validation, returning structured results."""

        shacl_result = self._run_shacl_validation(config, parser_output)
        tabular_result = self._run_tabular_checks(tables)
        diagnostics = self._generate_editorial_diagnostics(tables)
        return ValidationResult(shacl=shacl_result, tabular=tabular_result, diagnostics=diagnostics)

    # ------------------------------------------------------------------
    # SHACL
    # ------------------------------------------------------------------
    def _run_shacl_validation(
        self,
        config: SourceConfig,
        parser_output: Optional[ParserOutput],
    ) -> Dict[str, Any]:
        if pyshacl_validate is None:
            return {
                "status": "skipped",
                "reason": "pyshacl not available",
            }
        if not parser_output or not parser_output.materialized_graph_path:
            return {
                "status": "skipped",
                "reason": "no graph materialization available",
            }

        materialized_path = Path(parser_output.materialized_graph_path)
        data_graph = Graph()
        try:
            data_graph.parse(materialized_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse materialized graph for %s: %s", config.id, exc)
            return {
                "status": "error",
                "error": str(exc),
            }

        shapes_graph = self._shapes_graph
        if shapes_graph is None:
            shapes_graph = Graph()
            shapes_graph.parse(data=DEFAULT_SHACL_SHAPES, format="turtle")

        try:
            conforms, _, results_text = pyshacl_validate(
                data_graph,
                shacl_graph=shapes_graph,
                inference="rdfs",
                advanced=True,
                abort_on_first=False,
                meta_shacl=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("SHACL validation error for %s", config.id)
            return {
                "status": "error",
                "error": str(exc),
            }

        return {
            "status": "passed" if conforms else "failed",
            "conforms": conforms,
            "report": results_text,
        }

    # ------------------------------------------------------------------
    # Tabular checks
    # ------------------------------------------------------------------
    def _run_tabular_checks(self, tables: SnapshotTables) -> Dict[str, Any]:
        summary = {
            "status": "passed",
            "checks": [],
        }

        def _add_check(name: str, passed: bool, details: Optional[str] = None) -> None:
            summary["checks"].append(
                {
                    "name": name,
                    "status": "passed" if passed else "failed",
                    "details": details,
                }
            )
            if not passed:
                summary["status"] = "failed"

        concepts = tables.concepts.copy()
        relations = tables.relations.copy()
        labels = tables.labels.copy()

        if concepts.empty:
            _add_check("concepts.non_empty", False, "Concept table is empty")
            return summary

        _add_check("concepts.unique_ids", concepts["canonical_id"].is_unique)
        _add_check("concepts.pref_label_presence", concepts["preferred_label"].notna().any())

        concept_ids = set(concepts["canonical_id"].dropna().astype(str))

        if not relations.empty:
            valid_subjects = relations["subject_id"].isin(concept_ids).all()
            valid_objects = relations["object_id"].isin(concept_ids).all()
            _add_check("relations.subjects_exist", valid_subjects)
            _add_check("relations.objects_exist", valid_objects)

        if not labels.empty:
            labels_valid = labels["concept_id"].isin(concept_ids).all()
            non_empty_text = labels["text"].astype(str).str.strip().ne("").all()
            _add_check("labels.concept_fk", labels_valid)
            _add_check("labels.text_present", non_empty_text)

        if self._pandera_enabled:
            pandera_summary = self._run_pandera_checks(tables)
            summary["checks"].extend(pandera_summary["checks"])
            if pandera_summary["status"] == "failed":
                summary["status"] = "failed"
        else:
            summary["checks"].append(
                {
                    "name": "pandera",
                    "status": "skipped",
                    "details": "pandera checks disabled",
                }
            )

        return summary

    def _generate_editorial_diagnostics(self, tables: SnapshotTables) -> Dict[str, Any]:
        diagnostics: Dict[str, Any] = {
            "duplicate_labels": [],
            "conflicting_mappings": [],
            "definition_length_flags": [],
            "capitalization_flags": [],
        }

        labels = tables.labels.copy()
        if not labels.empty:
            labels["language"] = labels["language"].fillna("")
            preferred_series = labels.get("is_preferred")
            if preferred_series is None:
                preferred_series = pd.Series([False] * len(labels), index=labels.index)
            alt_mask = ~preferred_series.fillna(False).astype(bool)
            alt_labels = labels[alt_mask].copy()
            preferred_lookup = {
                (row.concept_id, (row.language or "")): str(row.text or "")
                for row in labels[preferred_series.fillna(False)].itertuples()
            }
            if not alt_labels.empty:
                duplicate_groups = (
                    alt_labels.groupby(["concept_id", "text", "language"], dropna=False)
                    .size()
                    .reset_index(name="count")
                )
                duplicate_groups = duplicate_groups[duplicate_groups["count"] > 1]
                for row in duplicate_groups.itertuples():
                    diagnostics["duplicate_labels"].append(
                        {
                            "concept_id": str(row.concept_id),
                            "label": row.text,
                            "language": row.language,
                            "count": int(row.count),
                            "reason": "duplicate_alt_label",
                        }
                    )

                for row in alt_labels.itertuples():
                    key = (row.concept_id, (row.language or ""))
                    preferred_text = preferred_lookup.get(key)
                    alt_text = str(getattr(row, "text", "") or "")
                    if not preferred_text:
                        continue
                    if preferred_text.strip().lower() == alt_text.strip().lower():
                        diagnostics["duplicate_labels"].append(
                            {
                                "concept_id": str(row.concept_id),
                                "label": alt_text,
                                "language": row.language or "",
                                "count": 1,
                                "reason": "matches_preferred_label",
                            }
                        )

            capitalization_flags: List[Dict[str, Any]] = []
            cap_seen: set[Tuple[str, str, str]] = set()
            for row in labels.itertuples():
                text = str(getattr(row, "text", "") or "")
                if not text:
                    continue
                concept_id = str(getattr(row, "concept_id", ""))
                is_preferred = bool(getattr(row, "is_preferred", False))

                if text.strip() != text:
                    key = (concept_id, text, "whitespace")
                    if key not in cap_seen:
                        cap_seen.add(key)
                        capitalization_flags.append(
                            {
                                "concept_id": concept_id,
                                "label": text,
                                "reason": "whitespace",
                            }
                        )

                if text.isupper() and len(text) > 4:
                    key = (concept_id, text, "all_caps")
                    if key not in cap_seen:
                        cap_seen.add(key)
                        capitalization_flags.append(
                            {
                                "concept_id": concept_id,
                                "label": text,
                                "reason": "all_caps",
                            }
                        )

                if is_preferred and text.islower() and len(text) > 4:
                    key = (concept_id, text, "preferred_lowercase")
                    if key not in cap_seen:
                        cap_seen.add(key)
                        capitalization_flags.append(
                            {
                                "concept_id": concept_id,
                                "label": text,
                                "reason": "preferred_lowercase",
                            }
                        )

            diagnostics["capitalization_flags"] = capitalization_flags

        mappings = tables.mappings
        if not mappings.empty and {"subject_id", "target_scheme", "target_id", "mapping_type"}.issubset(
            set(mappings.columns)
        ):
            conflict_groups = (
                mappings.groupby(["subject_id", "target_scheme", "target_id"])["mapping_type"]
                .nunique()
                .reset_index(name="mapping_type_count")
            )
            conflict_groups = conflict_groups[conflict_groups["mapping_type_count"] > 1]
            for row in conflict_groups.itertuples():
                subset = mappings[
                    (mappings["subject_id"] == row.subject_id)
                    & (mappings["target_scheme"] == row.target_scheme)
                    & (mappings["target_id"] == row.target_id)
                ]
                diagnostics["conflicting_mappings"].append(
                    {
                        "subject_id": str(row.subject_id),
                        "target_scheme": row.target_scheme,
                        "target_id": row.target_id,
                        "mapping_types": sorted(subset["mapping_type"].dropna().unique().tolist()),
                    }
                )

        concepts = tables.concepts
        if not concepts.empty and "definition" in concepts.columns:
            definitions = concepts[["canonical_id", "definition"]].dropna(subset=["definition"]).copy()
            if not definitions.empty:
                definitions["definition_length"] = definitions["definition"].astype(str).str.len()
                min_len = 15
                max_len = 400
                short_defs = definitions[definitions["definition_length"] < min_len]
                long_defs = definitions[definitions["definition_length"] > max_len]

                for row in short_defs.itertuples():
                    diagnostics["definition_length_flags"].append(
                        {
                            "concept_id": str(row.canonical_id),
                            "length": int(row.definition_length),
                            "severity": "too_short",
                        }
                    )

                for row in long_defs.itertuples():
                    diagnostics["definition_length_flags"].append(
                        {
                            "concept_id": str(row.canonical_id),
                            "length": int(row.definition_length),
                            "severity": "too_long",
                        }
                    )

        diagnostics["summary"] = {
            "duplicate_labels": len(diagnostics["duplicate_labels"]),
            "conflicting_mappings": len(diagnostics["conflicting_mappings"]),
            "definition_length_flags": len(diagnostics["definition_length_flags"]),
            "capitalization_flags": len(diagnostics["capitalization_flags"]),
        }
        return diagnostics

    def _run_pandera_checks(self, tables: SnapshotTables) -> Dict[str, Any]:
        summary = {
            "status": "passed",
            "checks": [],
        }

        def _pa_check(name: str, schema: pa.DataFrameSchema, df) -> None:
            try:
                schema.validate(df, lazy=True)
                summary["checks"].append({"name": name, "status": "passed", "details": None})
            except (pa.errors.SchemaError, pa.errors.SchemaErrors) as exc:
                summary["checks"].append(
                    {
                        "name": name,
                        "status": "failed",
                        "details": str(exc),
                    }
                )
                summary["status"] = "failed"

        concept_ids = tables.concepts["canonical_id"].dropna().astype(str)
        concept_id_values = concept_ids.unique().tolist()

        concepts_schema = pa.DataFrameSchema(
            {
                "canonical_id": pa.Column(
                    str,
                    checks=[pa.Check.str_length(min_value=1)],
                    nullable=False,
                    unique=True,
                ),
                "preferred_label": pa.Column(str, checks=[pa.Check.str_length(min_value=1)], nullable=False),
            },
            coerce=True,
        )
        _pa_check("pandera.concepts", concepts_schema, tables.concepts)

        if not tables.relations.empty:
            relations_schema = pa.DataFrameSchema(
                {
                    "subject_id": pa.Column(str, checks=[pa.Check.isin(concept_id_values)], nullable=False),
                    "object_id": pa.Column(str, checks=[pa.Check.isin(concept_id_values)], nullable=False),
                    "predicate": pa.Column(str, checks=[pa.Check.isin({"broader", "narrower"})], nullable=False),
                }
            )
            _pa_check("pandera.relations", relations_schema, tables.relations)

        if not tables.labels.empty:
            labels_schema = pa.DataFrameSchema(
                {
                    "concept_id": pa.Column(str, checks=[pa.Check.isin(concept_id_values)], nullable=False),
                    "text": pa.Column(str, checks=[pa.Check.str_length(min_value=1)], nullable=False),
                }
            )
            _pa_check("pandera.labels", labels_schema, tables.labels)

        return summary
