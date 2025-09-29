"""Parser utilities for SKOS/OWL/OBO sources."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

import owlready2
import pronto
from rdflib import Graph

from .models import ParserOutput, SourceConfig, SourceType

logger = logging.getLogger(__name__)


class ParserError(RuntimeError):
    """Raised when parsing fails."""


class SkosParser:
    """Parse SKOS files using rdflib."""

    def parse(self, config: SourceConfig, content: bytes, target_dir: Path) -> ParserOutput:
        graph = Graph()
        try:
            graph.parse(data=content, format=config.format or self._infer_format(config.location))
        except Exception as exc:  # noqa: BLE001
            raise ParserError(f"Failed to parse SKOS content for {config.id}: {exc}") from exc

        output_path = target_dir / f"{config.id}-graph.ttl"
        graph.serialize(destination=output_path, format="turtle")
        stats = {
            "triples": len(graph),
        }
        return ParserOutput(stats=stats, materialized_graph_path=output_path)

    def _infer_format(self, location: str) -> str:
        if location.endswith(".ttl") or location.endswith(".n3"):
            return "turtle"
        if location.endswith(".rdf") or location.endswith(".xml"):
            return "xml"
        if location.endswith(".json") or location.endswith(".jsonld"):
            return "json-ld"
        return "xml"


class OwlParser:
    """Parse OWL ontologies using owlready2."""

    def parse(self, config: SourceConfig, content: bytes, target_dir: Path) -> ParserOutput:
        tmp_path = target_dir / f"{config.id}.owl"
        tmp_path.write_bytes(content)
        try:
            ontology = owlready2.get_ontology(tmp_path.resolve().as_uri()).load()
        except Exception as exc:  # noqa: BLE001
            raise ParserError(f"Failed to load OWL ontology for {config.id}: {exc}") from exc

        cls_count = sum(1 for _ in ontology.classes())
        obj_properties = sum(1 for _ in ontology.object_properties())
        data_properties = sum(1 for _ in ontology.data_properties())
        stats = {
            "classes": cls_count,
            "object_properties": obj_properties,
            "data_properties": data_properties,
        }
        saved_path = target_dir / f"{config.id}-materialized.owl"
        ontology.save(file=str(saved_path))
        return ParserOutput(
            stats=stats,
            materialized_graph_path=saved_path,
            extras={"source_path": str(tmp_path)},
        )


class OboParser:
    """Parse OBO ontologies using pronto."""

    def parse(self, config: SourceConfig, content: bytes, target_dir: Path) -> ParserOutput:
        tmp_path = target_dir / f"{config.id}.obo"
        tmp_path.write_bytes(content)
        try:
            ontology = pronto.Ontology(str(tmp_path))
        except Exception as exc:  # noqa: BLE001
            raise ParserError(f"Failed to load OBO ontology for {config.id}: {exc}") from exc

        stats: Dict[str, int] = {
            "terms": len(list(ontology.terms())),
            "relationships": len(list(ontology.relationships())),
        }
        exported_path = target_dir / f"{config.id}-json.json"
        ontology.dump(exported_path, format="json")
        return ParserOutput(
            stats=stats,
            materialized_graph_path=exported_path,
            extras={"source_path": str(tmp_path)},
        )


class ParserFactory:
    """Factory returning the appropriate parser for a source config."""

    _PARSERS = {
        SourceType.SKOS: SkosParser,
        SourceType.OWL: OwlParser,
        SourceType.OBO: OboParser,
    }

    @classmethod
    def get_parser(cls, config: SourceConfig):
        parser_cls = cls._PARSERS.get(config.type)
        if not parser_cls:
            raise ParserError(f"Unsupported source type: {config.type}")
        return parser_cls()
