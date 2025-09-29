"""Normalization pipeline for SKOS, OWL, and OBO sources."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS

from .canonical import (
    ConceptRecord,
    LabelRecord,
    MappingRecord,
    RelationRecord,
    SnapshotTables,
)
from .models import ParserOutput, SourceConfig, SourceType
from .parsers import OboParser, OwlParser, ParserError, SkosParser

logger = logging.getLogger(__name__)


@dataclass
class NormalizationResult:
    tables: SnapshotTables
    parser_output: Optional[ParserOutput]


class NormalizationPipeline:
    """Convert raw KOS formats into canonical tables."""

    def __init__(self, prefix_map: Optional[Mapping[str, str]] = None) -> None:
        self.prefix_map = prefix_map or {}
        self.skos_parser = SkosParser()
        self.owl_parser = OwlParser()
        self.obo_parser = OboParser()

    def run(self, config: SourceConfig, content: bytes) -> NormalizationResult:
        temp_dir = self._temp_dir(config)
        if config.type is SourceType.SKOS:
            parser_output = self.skos_parser.parse(config, content, target_dir=temp_dir)
            graph = Graph()
            graph.parse(data=content, format=config.format or self._guess_format(config))
            tables = self._normalize_skos(config, graph)
        elif config.type is SourceType.OWL:
            parser_output = self.owl_parser.parse(config, content, target_dir=temp_dir)
            graph = Graph()
            graph.parse(data=content, format=config.format or self._guess_format(config) or "xml")
            tables = self._normalize_owl(config, graph)
        elif config.type is SourceType.OBO:
            parser_output = self.obo_parser.parse(config, content, target_dir=temp_dir)
            tables = self._normalize_obo(config, parser_output)
        else:
            raise ParserError(f"Unsupported source type: {config.type}")
        return NormalizationResult(tables=tables, parser_output=parser_output)

    def _normalize_skos(self, config: SourceConfig, graph: Graph) -> SnapshotTables:
        concepts: List[ConceptRecord] = []
        labels: List[LabelRecord] = []
        relations: List[RelationRecord] = []
        mappings: List[MappingRecord] = []

        skos_concepts = self._gather_skos_subjects(graph)

        for subject in skos_concepts:
            canonical_id = str(subject)
            source_id = canonical_id
            preferred_labels = list(graph.objects(subject, SKOS.prefLabel))
            alt_labels = list(graph.objects(subject, SKOS.altLabel))
            notes = list(graph.objects(subject, SKOS.definition))
            scope_notes = list(graph.objects(subject, SKOS.scopeNote))
            broader_nodes = [str(obj) for obj in graph.objects(subject, SKOS.broader)]
            narrower_nodes = [str(obj) for obj in graph.objects(subject, SKOS.narrower)]

            preferred_label, language = self._select_preferred_label(preferred_labels)

            provenance = self._provenance(config.id, subject, graph)
            depth, path_to_root = self._compute_depth_and_path(graph, subject)
            is_leaf = len(narrower_nodes) == 0
            concepts.append(
                ConceptRecord(
                    canonical_id=canonical_id,
                    source_id=source_id,
                    source_scheme=config.id,
                    preferred_label=preferred_label,
                    definition=self._first_text(notes) or self._first_text(scope_notes),
                    language=language,
                    depth=depth,
                    is_leaf=is_leaf,
                    is_deprecated=self._is_deprecated(graph, subject),
                    path_to_root=path_to_root,
                    provenance=provenance,
                )
            )

            labels.extend(self._build_label_records(canonical_id, preferred_labels, is_pref=True))
            labels.extend(self._build_label_records(canonical_id, alt_labels, is_pref=False))

            for broader in broader_nodes:
                relations.append(
                    RelationRecord(subject_id=canonical_id, predicate="broader", object_id=broader)
                )
            for narrower in narrower_nodes:
                relations.append(
                    RelationRecord(subject_id=canonical_id, predicate="narrower", object_id=narrower)
                )

            mappings.extend(self._collect_mappings(graph, subject, config.id))

        return SnapshotTables.from_records(concepts, labels, relations, mappings)

    def _normalize_owl(self, config: SourceConfig, graph: Graph) -> SnapshotTables:
        concepts: List[ConceptRecord] = []
        labels: List[LabelRecord] = []
        relations: List[RelationRecord] = []
        mappings: List[MappingRecord] = []

        owl_classes = set(graph.subjects(RDF.type, OWL.Class))
        for subject in owl_classes:
            canonical_id = str(subject)
            preferred_labels = list(graph.objects(subject, SKOS.prefLabel)) or list(
                graph.objects(subject, RDFS.label)
            )
            alt_labels = list(graph.objects(subject, SKOS.altLabel))
            definitions = list(graph.objects(subject, SKOS.definition)) or list(
                graph.objects(subject, RDFS.comment)
            )
            broader_nodes = [str(obj) for obj in graph.objects(subject, RDFS.subClassOf) if isinstance(obj, URIRef)]
            narrower_nodes = [str(subj) for subj in graph.subjects(RDFS.subClassOf, subject) if isinstance(subj, URIRef)]

            preferred_label, language = self._select_preferred_label(preferred_labels)

            depth, path_to_root = self._compute_depth_and_path(
                graph,
                subject,
                parent_predicate=RDFS.subClassOf,
            )
            concepts.append(
                ConceptRecord(
                    canonical_id=canonical_id,
                    source_id=canonical_id,
                    source_scheme=config.id,
                    preferred_label=preferred_label,
                    definition=self._first_text(definitions),
                    language=language,
                    depth=depth,
                    is_leaf=len(narrower_nodes) == 0,
                    is_deprecated=self._is_deprecated(graph, subject),
                    path_to_root=path_to_root,
                    provenance=self._provenance(config.id, subject, graph),
                )
            )

            labels.extend(self._build_label_records(canonical_id, preferred_labels, is_pref=True))
            labels.extend(self._build_label_records(canonical_id, alt_labels, is_pref=False))

            for superclass in broader_nodes:
                relations.append(
                    RelationRecord(subject_id=canonical_id, predicate="broader", object_id=superclass)
                )
            for subclass in narrower_nodes:
                relations.append(
                    RelationRecord(subject_id=canonical_id, predicate="narrower", object_id=subclass)
                )

            mappings.extend(self._collect_mappings(graph, subject, config.id))

        return SnapshotTables.from_records(concepts, labels, relations, mappings)

    def _normalize_obo(self, config: SourceConfig, parser_output: ParserOutput) -> SnapshotTables:
        concepts: List[ConceptRecord] = []
        labels: List[LabelRecord] = []
        relations: List[RelationRecord] = []
        mappings: List[MappingRecord] = []

        from pronto import Ontology

        ontology_path = parser_output.extras.get("source_path")
        if not ontology_path:
            return SnapshotTables.from_records(concepts, labels, relations, mappings)

        ontology = Ontology(str(ontology_path))
        for term in ontology.terms():
            canonical_id = term.id
            preferred_label = term.name
            language = term.other.get("default-namespace", [None])[0]
            parent_ids = [parent.id for parent in term.superclasses(distance=1) if parent.id != term.id]
            child_ids = [child.id for child in term.subclasses(distance=1) if child.id != term.id]

            depth, path_to_root = self._compute_obo_depth_and_path(term, parent_ids)
            concepts.append(
                ConceptRecord(
                    canonical_id=canonical_id,
                    source_id=term.id,
                    source_scheme=config.id,
                    preferred_label=preferred_label,
                    definition=term.definition or None,
                    language=language,
                    depth=max(depth, 0),
                    is_leaf=len(child_ids) == 0,
                    is_deprecated=term.obsolete,
                    path_to_root=path_to_root,
                    provenance={"source_scheme": config.id, "source_identifier": term.id},
                )
            )

            labels.append(
                LabelRecord(
                    concept_id=canonical_id,
                    text=preferred_label or term.id,
                    language=None,
                    is_preferred=True,
                    kind="pref",
                )
            )
            for synonym in term.synonyms:
                labels.append(
                    LabelRecord(
                        concept_id=canonical_id,
                        text=synonym.description or synonym.name,
                        language=None,
                        is_preferred=False,
                        kind="alt",
                    )
                )

            for parent_id in parent_ids:
                relations.append(
                    RelationRecord(subject_id=canonical_id, predicate="broader", object_id=parent_id)
                )
            for child_id in child_ids:
                relations.append(
                    RelationRecord(subject_id=canonical_id, predicate="narrower", object_id=child_id)
                )

        return SnapshotTables.from_records(concepts, labels, relations, mappings)

    def _select_preferred_label(self, labels: Sequence[Literal]) -> Tuple[Optional[str], Optional[str]]:
        for literal in labels:
            if isinstance(literal, Literal):
                return str(literal), literal.language
        if labels:
            return str(labels[0]), None
        return None, None

    def _build_label_records(
        self,
        concept_id: str,
        values: Sequence[Literal],
        *,
        is_pref: bool,
    ) -> List[LabelRecord]:
        records: List[LabelRecord] = []
        for value in values:
            language = value.language if isinstance(value, Literal) else None
            text = str(value)
            records.append(
                LabelRecord(
                    concept_id=concept_id,
                    text=text,
                    language=language,
                    is_preferred=is_pref,
                    kind="pref" if is_pref else "alt",
                )
            )
        return records

    def _collect_mappings(
        self,
        graph: Graph,
        subject,
        source_scheme: str,
    ) -> List[MappingRecord]:
        mapping_predicates = {
            SKOS.exactMatch: "exactMatch",
            SKOS.closeMatch: "closeMatch",
            SKOS.relatedMatch: "relatedMatch",
            SKOS.broadMatch: "broadMatch",
            SKOS.narrowMatch: "narrowMatch",
        }
        mappings: List[MappingRecord] = []
        for predicate, mapping_type in mapping_predicates.items():
            for obj in graph.objects(subject, predicate):
                mappings.append(
                    MappingRecord(
                        subject_id=str(subject),
                        mapping_type=mapping_type,
                        target_scheme=self._infer_scheme(str(obj)) or source_scheme,
                        target_id=str(obj),
                    )
                )
        return mappings

    def _is_deprecated(self, graph: Graph, subject) -> bool:
        for prop in (OWL.deprecated, DCTERMS.isReplacedBy):
            for value in graph.objects(subject, prop):
                if isinstance(value, Literal) and str(value).lower() == "true":
                    return True
                if isinstance(prop, URIRef) and prop == DCTERMS.isReplacedBy:
                    return True
        return False

    def _first_text(self, values: Sequence[Literal]) -> Optional[str]:
        for value in values:
            return str(value)
        return None

    def _temp_dir(self, config: SourceConfig):  # pragma: no cover - simple helper
        from pathlib import Path

        path = Path(".artifacts") / config.id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _guess_format(self, config: SourceConfig) -> Optional[str]:
        if config.format:
            return config.format
        location = config.location.lower()
        if location.endswith(".ttl") or location.endswith(".n3"):
            return "turtle"
        if location.endswith(".rdf") or location.endswith(".xml"):
            return "xml"
        if location.endswith(".json") or location.endswith(".jsonld"):
            return "json-ld"
        return None

    def _compute_depth_and_path(
        self,
        graph: Graph,
        subject: URIRef,
        *,
        parent_predicate: URIRef = SKOS.broader,
        max_depth: int = 32,
    ) -> Tuple[int, Tuple[str, ...]]:
        visited: set = set()
        queue: List[Tuple[URIRef, Tuple[str, ...]]] = [(subject, tuple())]
        best_depth = 0
        best_path: Tuple[str, ...] = tuple()

        while queue:
            current, path = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if len(path) > best_depth:
                best_depth = len(path)
                best_path = path
            if len(path) >= max_depth:
                continue
            for parent in graph.objects(current, parent_predicate):
                if isinstance(parent, URIRef) and parent not in path:
                    queue.append((parent, path + (str(parent),)))

        return best_depth, best_path

    def _compute_obo_depth_and_path(
        self,
        term,
        parent_ids: Sequence[str],
    ) -> Tuple[int, Tuple[str, ...]]:
        try:
            ancestors = list(term.superclasses(distance=None))
        except TypeError:
            ancestors = []

        if not ancestors:
            return 0, tuple(parent_ids)

        unique_ids = [ancestor.id for ancestor in ancestors if getattr(ancestor, "id", None)]
        depth = max(len(unique_ids) - 1, 0)
        return depth, tuple(parent_ids)

    def _gather_skos_subjects(self, graph: Graph) -> Iterable[URIRef]:
        subjects: Dict[URIRef, None] = {}
        predicates = (
            SKOS.prefLabel,
            SKOS.altLabel,
            SKOS.definition,
            SKOS.scopeNote,
            SKOS.broader,
            SKOS.narrower,
            SKOS.topConceptOf,
        )
        for subject in graph.subjects(RDF.type, SKOS.Concept):
            subjects[subject] = None
        for predicate in predicates:
            for subject in graph.subjects(predicate=predicate):
                if isinstance(subject, URIRef):
                    subjects[subject] = None
        return subjects.keys()

    def _provenance(self, scheme: str, subject: URIRef, graph: Graph) -> Dict[str, str]:
        provenance: Dict[str, str] = {
            "source_scheme": scheme,
            "source_identifier": str(subject),
        }
        for predicate in (DCTERMS.issued, DCTERMS.modified):
            for value in graph.objects(subject, predicate):
                provenance[str(predicate)] = str(value)
        return provenance

    def _infer_scheme(self, identifier: str) -> Optional[str]:
        if ":" in identifier and not identifier.startswith("http"):
            return identifier.split(":", 1)[0]
        if "//" in identifier:
            host_part = identifier.split("//", 1)[1]
            return host_part.split("/", 1)[0]
        return None
