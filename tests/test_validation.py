from __future__ import annotations

from DomainDetermine.kos_ingestion.canonical import (
    ConceptRecord,
    LabelRecord,
    MappingRecord,
    RelationRecord,
    SnapshotTables,
)
from DomainDetermine.kos_ingestion.models import SourceConfig, SourceType
from DomainDetermine.kos_ingestion.validation import KOSValidator


def make_tables() -> SnapshotTables:
    short_definition = "short"
    long_definition = "L" * 450
    concepts = [
        ConceptRecord(
            canonical_id="R1",
            source_id="R1",
            source_scheme="test",
            preferred_label="Root",
            definition=short_definition,
            language="en",
            depth=0,
            is_leaf=False,
            is_deprecated=False,
            path_to_root=tuple(),
            provenance={},
        ),
        ConceptRecord(
            canonical_id="R2",
            source_id="R2",
            source_scheme="test",
            preferred_label="child",
            definition=long_definition,
            language="en",
            depth=1,
            is_leaf=True,
            is_deprecated=False,
            path_to_root=("R1",),
            provenance={},
        ),
    ]
    labels = [
        LabelRecord(concept_id="R1", text="Duplicate", language="en", is_preferred=False, kind="alt"),
        LabelRecord(concept_id="R1", text="Duplicate", language="en", is_preferred=False, kind="alt"),
        LabelRecord(concept_id="R2", text="child", language="en", is_preferred=True, kind="pref"),
        LabelRecord(concept_id="R2", text="SCREAM", language="en", is_preferred=False, kind="alt"),
    ]
    relations = [
        RelationRecord(subject_id="R1", predicate="narrower", object_id="R2"),
        RelationRecord(subject_id="R2", predicate="broader", object_id="R1"),
    ]
    mappings = [
        MappingRecord(subject_id="R1", mapping_type="exactMatch", target_scheme="ext", target_id="E1"),
        MappingRecord(subject_id="R1", mapping_type="closeMatch", target_scheme="ext", target_id="E1"),
    ]
    return SnapshotTables.from_records(concepts, labels, relations, mappings)


def test_editorial_diagnostics_detects_flags() -> None:
    validator = KOSValidator()
    tables = make_tables()
    config = SourceConfig(id="test", type=SourceType.SKOS, location="file.ttl")

    result = validator.validate(config, tables, parser_output=None)
    diagnostics = result.diagnostics

    assert diagnostics["duplicate_labels"], "Expected duplicate label diagnostics"
    assert diagnostics["conflicting_mappings"], "Expected conflicting mapping diagnostics"
    severities = {flag["severity"] for flag in diagnostics["definition_length_flags"]}
    assert {"too_short", "too_long"}.issubset(severities)

    reasons = {flag["reason"] for flag in diagnostics["capitalization_flags"]}
    assert {"preferred_lowercase", "all_caps"}.issubset(reasons)

    summary = diagnostics["summary"]
    assert summary["duplicate_labels"] == len(diagnostics["duplicate_labels"])
    assert summary["conflicting_mappings"] == len(diagnostics["conflicting_mappings"])
