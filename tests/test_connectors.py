from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pytest
from requests import Session

from DomainDetermine.kos_ingestion.config import load_policies, load_source_configs
from DomainDetermine.kos_ingestion.fetchers import CheckedResponse, HttpFetcher, SparqlFetcher
from DomainDetermine.kos_ingestion.models import (
    ConnectorContext,
    DeltaStrategy,
    LicensingPolicy,
    SourceConfig,
    SourceType,
)
from DomainDetermine.kos_ingestion.parsers import ParserFactory
from DomainDetermine.kos_ingestion.pipeline import IngestConnector


class DummyHttpFetcher(HttpFetcher):
    def __init__(self, content_map: Dict[str, bytes]) -> None:
        super().__init__()
        self.content_map = content_map

    def fetch(self, config: SourceConfig, context: ConnectorContext) -> CheckedResponse:  # type: ignore[override]
        content = self.content_map.get(config.location)
        if content is None:
            raise RuntimeError("missing content for test")
        headers = {"ETag": "test-etag", "Last-Modified": "Wed, 01 Jan 2025 00:00:00 GMT"}
        return CheckedResponse(content=content, status_code=200, headers=headers)


class DummySparqlFetcher(SparqlFetcher):
    def __init__(self, response: Dict) -> None:
        super().__init__()
        self.response = response

    def fetch(self, config, context):  # type: ignore[override]
        content = json.dumps(self.response).encode("utf-8")
        return CheckedResponse(content=content, status_code=200, headers={})


@pytest.fixture
def artifact_root(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"


@pytest.fixture
def context(artifact_root: Path) -> ConnectorContext:
    policy = LicensingPolicy(name="test", allow_raw_exports=False, restricted_fields={"pref_label"})
    return ConnectorContext(artifact_root=artifact_root, policies={"test": policy})


def test_load_configs_and_policies(tmp_path: Path) -> None:
    config_path = tmp_path / "sources.json"
    config_path.write_text(
        json.dumps(
            [
                {
                    "id": "local",
                    "type": "skos",
                    "location": "file.ttl",
                    "license_name": "test",
                }
            ]
        )
    )
    policy_path = tmp_path / "policies.json"
    policy_path.write_text(
        json.dumps(
            [
                {
                    "name": "test",
                    "allow_raw_exports": False,
                    "restricted_fields": ["pref_label"],
                }
            ]
        )
    )

    configs = load_source_configs(config_path)
    policies = load_policies(policy_path)

    assert configs[0].type is SourceType.SKOS
    assert policies["test"].requires_masking("pref_label")


def test_ingest_local_skos(tmp_path: Path, context: ConnectorContext) -> None:
    ttl_content = b"""@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n<http://example.com/A> skos:prefLabel \"Concept A\"@en .\n"""
    local_path = tmp_path / "local.ttl"
    local_path.write_bytes(ttl_content)

    config = SourceConfig(
        id="local",
        type=SourceType.SKOS,
        location=str(local_path),
        license_name="test",
    )

    connector = IngestConnector(context=context)
    result = connector.run(config)

    assert result.metadata.checksum is not None
    assert result.metadata.export_allowed is False
    assert result.parser_output is not None
    assert result.parser_output.stats["triples"] == 1
    tabular_summary = result.metadata.extra["validation"]["tabular"]
    assert tabular_summary["status"] == "passed"
    check_names = {check["name"] for check in tabular_summary["checks"]}
    assert {"concepts.unique_ids", "concepts.pref_label_presence", "pandera.concepts"}.issubset(check_names)
    assert result.query_service is not None
    concept = result.query_service.get_concept("http://example.com/A")
    assert concept["canonical_id"] == "http://example.com/A"


def test_ingest_remote_with_custom_fetcher(tmp_path: Path, context: ConnectorContext) -> None:
    config = SourceConfig(
        id="remote",
        type=SourceType.OWL,
        location="https://example.com/ontology.owl",
        license_name="test",
    )
    fake_content = b"<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'></rdf:RDF>"

    connector = IngestConnector(
        context=context,
        http_fetcher=DummyHttpFetcher({config.location: fake_content}),
    )

    result = connector.run(config)
    assert result.metadata.checksum is not None
    assert result.metadata.delta == "changed"
    assert result.parser_output is not None
    assert "validation" in result.metadata.extra


def test_skip_delta_when_etag_matches(tmp_path: Path, context: ConnectorContext) -> None:
    config = SourceConfig(
        id="remote",
        type=SourceType.OBO,
        location="https://example.com/ontology.obo",
        license_name="test",
        delta_strategy=DeltaStrategy.ETAG,
    )

    content = b"format-version: 1.2\n"  # minimal OBO header
    fetcher = DummyHttpFetcher({config.location: content})
    connector = IngestConnector(context=context, http_fetcher=fetcher)

    result1 = connector.run(config)
    assert result1.metadata.delta == "changed"

    result2 = connector.run(config)
    assert result2.metadata.delta == "unchanged"


def test_sparql_fetch(tmp_path: Path, context: ConnectorContext) -> None:
    config = SourceConfig(
        id="wikidata",
        type=SourceType.SPARQL,
        location="https://query.wikidata.org/sparql",
        sparql_query="SELECT * WHERE {?s ?p ?o} LIMIT 1",
        cache_ttl_seconds=120,
    )

    fetcher = DummySparqlFetcher({"results": {"bindings": []}})
    connector = IngestConnector(context=context, sparql_fetcher=fetcher)
    result = connector.run(config)

    assert result.metadata.source_type is SourceType.SPARQL
    assert result.parser_output is None
    assert "validation" not in result.metadata.extra


def test_parser_factory_returns_correct_parser() -> None:
    config = SourceConfig(id="x", type=SourceType.SKOS, location="x")
    parser = ParserFactory.get_parser(config)
    from DomainDetermine.kos_ingestion.parsers import SkosParser

    assert isinstance(parser, SkosParser)


def test_http_fetcher_uses_cache_rate_limit_and_secrets(tmp_path: Path) -> None:
    config = SourceConfig(
        id="cached",
        type=SourceType.SKOS,
        location="https://example.com/cached.ttl",
        cache_ttl_seconds=3600,
        rate_limit_per_second=10.0,
        credential_secret="example",
        headers={"X-Custom": "value"},
        delta_strategy=DeltaStrategy.CHECKSUM,
    )

    def resolve_secret(name: str) -> Dict[str, str]:
        assert name == "example"
        return {"Authorization": "Bearer token"}

    context = ConnectorContext(artifact_root=tmp_path / "artifacts", secret_resolver=resolve_secret)

    content = b"@prefix skos: <http://www.w3.org/2004/02/skos/core#> ."

    class SingleShotSession(Session):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0
            self.last_headers: Dict[str, str] | None = None

        def get(self, *args, **kwargs):  # type: ignore[override]
            self.calls += 1
            self.last_headers = kwargs.get("headers") or {}
            return type(
                "Resp",
                (),
                {
                    "status_code": 200,
                    "content": content,
                    "headers": {"ETag": "cache", "Last-Modified": "Wed, 01 Jan 2025 00:00:00 GMT"},
                },
            )()

    session = SingleShotSession()
    fetcher = HttpFetcher(session=session)

    first = fetcher.fetch(config, context)
    second = fetcher.fetch(config, context)

    assert first.content == content
    assert second.content == content
    assert session.calls == 1
    assert session.last_headers is not None
    assert session.last_headers.get("Authorization") == "Bearer token"
