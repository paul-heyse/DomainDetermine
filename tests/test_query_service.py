from __future__ import annotations

import pytest

from DomainDetermine.kos_ingestion.canonical import (
    ConceptRecord,
    LabelRecord,
    MappingRecord,
    RelationRecord,
    SnapshotTables,
)
from DomainDetermine.kos_ingestion.query import QueryConfig, SnapshotQueryService


@pytest.fixture
def snapshot_tables() -> SnapshotTables:
    concepts = [
        ConceptRecord(
            canonical_id="C1",
            source_id="S1",
            source_scheme="test",
            preferred_label="Root",
            definition="root concept",
            language="en",
            depth=0,
            is_leaf=False,
            is_deprecated=False,
            path_to_root=tuple(),
            provenance={"source": "fixture"},
        ),
        ConceptRecord(
            canonical_id="C2",
            source_id="S2",
            source_scheme="test",
            preferred_label="Child",
            definition="child concept",
            language="en",
            depth=1,
            is_leaf=True,
            is_deprecated=False,
            path_to_root=("C1",),
            provenance={"source": "fixture"},
        ),
    ]
    labels = [
        LabelRecord(concept_id="C1", text="Root", language="en", is_preferred=True, kind="pref"),
        LabelRecord(concept_id="C2", text="Child", language="en", is_preferred=True, kind="pref"),
        LabelRecord(concept_id="C2", text="Kid", language="en", is_preferred=False, kind="alt"),
    ]
    relations = [
        RelationRecord(subject_id="C1", predicate="narrower", object_id="C2"),
        RelationRecord(subject_id="C2", predicate="broader", object_id="C1"),
    ]
    mappings = [
        MappingRecord(subject_id="C2", mapping_type="exactMatch", target_scheme="other", target_id="O1"),
    ]
    return SnapshotTables.from_records(concepts, labels, relations, mappings)


def test_get_concept(snapshot_tables: SnapshotTables) -> None:
    service = SnapshotQueryService(snapshot_tables)
    concept = service.get_concept("C1")
    assert concept is not None
    assert concept["preferred_label"] == "Root"
    assert concept["labels"]
    assert concept["relations"]["narrower"] == ["C2"]


def test_subtree(snapshot_tables: SnapshotTables) -> None:
    service = SnapshotQueryService(snapshot_tables)
    subtree = service.subtree("C1")
    assert set(subtree) == {"C1", "C2"}


def test_search_labels(snapshot_tables: SnapshotTables) -> None:
    service = SnapshotQueryService(snapshot_tables)
    matches = service.search_labels("Child")
    assert matches
    assert matches[0]["concept_id"] == "C2"


def test_sparql_gateway_cache(snapshot_tables: SnapshotTables, monkeypatch) -> None:
    class FakeResult:
        def __init__(self, payload):
            self._payload = payload

        def convert(self):
            return self._payload

    class FakeClient:
        def __init__(self, url):
            self.url = url
            self.query_text = None

        def setReturnFormat(self, fmt):
            return None

        def setTimeout(self, timeout):
            return None

        def addCustomHttpHeader(self, key, value):
            return None

        def setQuery(self, query):
            self.query_text = query

        def query(self):
            return FakeResult({"results": {"bindings": [{"x": {"value": "1"}}]}})

    monkeypatch.setattr("DomainDetermine.kos_ingestion.query.SPARQLWrapper", FakeClient)

    service = SnapshotQueryService(snapshot_tables, config=QueryConfig())
    out1 = service.sparql_query(
        "https://example.com/sparql",
        "SELECT * WHERE {?s ?p ?o}",
        snapshot_version="v1",
    )
    assert out1["from_cache"] is False
    assert service.sparql_metrics["total"] == 1
    out2 = service.sparql_query(
        "https://example.com/sparql",
        "SELECT * WHERE {?s ?p ?o}",
        snapshot_version="v1",
    )
    assert out2["from_cache"] is True
    assert service.sparql_metrics["cache_hits"] == 1


def test_sparql_gateway_enforces_whitelist(snapshot_tables: SnapshotTables) -> None:
    service = SnapshotQueryService(snapshot_tables)
    with pytest.raises(ValueError):
        service.sparql_query("https://example.com/sparql", "DELETE WHERE {?s ?p ?o}")

