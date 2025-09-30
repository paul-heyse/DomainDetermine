"""Query service for KOS snapshots."""

from __future__ import annotations

import copy
import logging
import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
)

import duckdb
import pandas as pd
from rapidfuzz import process
from SPARQLWrapper import JSON as SPARQL_JSON
from SPARQLWrapper import SPARQLWrapper

from .canonical import SnapshotTables
from .models import QueryMetrics

logger = logging.getLogger(__name__)


@dataclass
class QueryConfig:
    max_subtree_size: int = 5000
    concept_cache_size: int = 512
    subtree_cache_size: int = 256
    label_search_cache_size: int = 256
    relation_cache_size: int = 256
    fuzzy_match_limit: int = 25
    fuzzy_score_cutoff: float = 70.0
    enable_semantic_fallback: bool = True
    sparql_timeout_seconds: int = 20
    sparql_max_rows: int = 5000
    sparql_cache_ttl_seconds: int = 600
    sparql_allowed_starts: Sequence[str] = ("SELECT", "ASK", "CONSTRUCT", "DESCRIBE")
    sparql_disallowed_keywords: Sequence[str] = (
        "INSERT",
        "DELETE",
        "LOAD",
        "CLEAR",
        "DROP",
        "CREATE",
        "MOVE",
        "COPY",
        "ADD",
    )
    sparql_allowed_endpoints: Sequence[str] = ()


K = TypeVar("K")
V = TypeVar("V")


class SemanticLabelIndex(Protocol):
    """Protocol describing a semantic label search index."""

    def search(self, query: str, *, lang: Optional[str], limit: int) -> Sequence[Mapping[str, Any]]:
        ...


class LRUCache(Generic[K, V]):
    """Minimal LRU cache used by the query service."""

    def __init__(self, maxsize: int) -> None:
        self.maxsize = max(0, maxsize)
        self._store: "OrderedDict[K, V]" = OrderedDict()

    def get(self, key: K) -> Optional[V]:
        if self.maxsize <= 0:
            return None
        try:
            value = self._store[key]
        except KeyError:
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: K, value: V) -> None:
        if self.maxsize <= 0:
            return
        self._store[key] = value
        self._store.move_to_end(key)
        while len(self._store) > self.maxsize:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()


FrozenRecord = Tuple[Tuple[str, Any], ...]
FrozenRecords = Tuple[FrozenRecord, ...]


def _freeze_records(records: Iterable[Mapping[str, Any]]) -> FrozenRecords:
    return tuple(tuple(sorted(item.items())) for item in records)


def _thaw_records(records: FrozenRecords) -> List[Dict[str, Any]]:
    return [dict(item) for item in records]


class SnapshotQueryService:
    """Provides read APIs over `SnapshotTables` with caching and DuckDB.

    The service is constructed from a `SnapshotTables` instance and maintains
    in-process DuckDB connections for analytics-oriented queries while offering
    high-level traversal helpers based on pandas DataFrames.
    """

    def __init__(
        self,
        tables: SnapshotTables,
        *,
        config: Optional[QueryConfig] = None,
        metrics: Optional[QueryMetrics] = None,
        semantic_index: Optional[SemanticLabelIndex] = None,
    ) -> None:
        self.tables = tables
        self.config = config or QueryConfig()
        self.metrics = metrics or QueryMetrics()
        self.semantic_index = semantic_index
        self._duckdb = duckdb.connect(database=":memory:")
        self._register_tables()
        self._sparql_cache: Dict[str, Dict[str, Any]] = {}
        self.sparql_metrics: Dict[str, Any] = {
            "total": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "durations": [],
        }
        self._concept_cache: LRUCache[str, Dict[str, Any]] = LRUCache(self.config.concept_cache_size)
        self._subtree_cache: LRUCache[Tuple[str, Optional[int]], Tuple[str, ...]] = LRUCache(
            self.config.subtree_cache_size
        )
        self._label_search_cache: LRUCache[
            Tuple[str, Optional[str], int, float, bool],
            FrozenRecords,
        ] = LRUCache(self.config.label_search_cache_size)

    # ------------------------------------------------------------------
    # DuckDB registration
    # ------------------------------------------------------------------
    def _register_tables(self) -> None:
        self._register_dataframe("concepts", self.tables.concepts)
        self._register_dataframe("labels", self.tables.labels)
        self._register_dataframe("relations", self.tables.relations)
        self._register_dataframe("mappings", self.tables.mappings)
        self._register_dataframe("paths", self.tables.paths)

    def _register_dataframe(self, name: str, df: pd.DataFrame) -> None:
        if df.empty:
            df = pd.DataFrame({"_": []})
        self._duckdb.register(name, df)

    # ------------------------------------------------------------------
    # Concept retrieval
    # ------------------------------------------------------------------
    def get_concept(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Return the canonical concept row with labels, mappings, and relations."""

        self.metrics.incr("query.get_concept.requests")
        start = time.perf_counter()

        cached = self._concept_cache.get(identifier)
        if cached is not None:
            self.metrics.incr("cache.concept.hit")
            duration = time.perf_counter() - start
            self.metrics.observe("query.get_concept.duration_seconds", duration)
            return copy.deepcopy(cached)

        self.metrics.incr("cache.concept.miss")
        concept = self.tables.concepts[self.tables.concepts["canonical_id"] == identifier]
        if concept.empty:
            concept = self.tables.concepts[self.tables.concepts["source_id"] == identifier]
        if concept.empty:
            duration = time.perf_counter() - start
            self.metrics.observe("query.get_concept.duration_seconds", duration)
            return None

        concept_row: Dict[str, Any] = concept.iloc[0].to_dict()
        canonical_id = concept_row.get("canonical_id")
        concept_row["labels"] = self._labels_for_concept(canonical_id)
        concept_row["mappings"] = self._mappings_for_concept(canonical_id)
        concept_row["relations"] = self._relations_for_concept(canonical_id)

        # Cache the hydrated concept under both canonical and source identifiers.
        self._concept_cache.set(identifier, concept_row)
        if canonical_id and canonical_id != identifier:
            self._concept_cache.set(canonical_id, concept_row)
        source_id = concept_row.get("source_id")
        if source_id and source_id not in {identifier, canonical_id}:
            self._concept_cache.set(str(source_id), concept_row)

        duration = time.perf_counter() - start
        self.metrics.observe("query.get_concept.duration_seconds", duration)
        return copy.deepcopy(concept_row)

    def _labels_for_concept(self, concept_id: str) -> List[Dict[str, object]]:
        if not concept_id:
            return []
        subset = self.tables.labels[self.tables.labels["concept_id"] == concept_id]
        return subset.to_dict(orient="records")

    def _mappings_for_concept(self, concept_id: str) -> List[Dict[str, object]]:
        if "subject_id" not in self.tables.mappings.columns:
            return []
        if not concept_id:
            return []
        subset = self.tables.mappings[self.tables.mappings["subject_id"] == concept_id]
        return subset.to_dict(orient="records")

    def _relations_for_concept(self, concept_id: str) -> Dict[str, List[str]]:
        if "subject_id" not in self.tables.relations.columns:
            return {}
        if not concept_id:
            return {}
        subset = self.tables.relations[self.tables.relations["subject_id"] == concept_id]
        result = {}
        for predicate, group in subset.groupby("predicate"):
            result[predicate] = group["object_id"].tolist()
        return result

    # ------------------------------------------------------------------
    # Traversal helpers
    # ------------------------------------------------------------------
    def list_children(self, concept_id: str) -> List[str]:
        return self._relations.get("narrower", concept_id)

    def list_parents(self, concept_id: str) -> List[str]:
        return self._relations.get("broader", concept_id)

    def list_siblings(self, concept_id: str) -> List[str]:
        parents = self.list_parents(concept_id)
        siblings: List[str] = []
        for parent in parents:
            siblings.extend([child for child in self.list_children(parent) if child != concept_id])
        return list(dict.fromkeys(siblings))

    def subtree(self, concept_id: str, *, max_depth: Optional[int] = None) -> List[str]:
        self.metrics.incr("query.subtree.requests")
        cache_key = (concept_id, max_depth)
        start = time.perf_counter()
        cached = self._subtree_cache.get(cache_key)
        if cached is not None:
            self.metrics.incr("cache.subtree.hit")
            duration = time.perf_counter() - start
            self.metrics.observe("query.subtree.duration_seconds", duration)
            return list(cached)

        self.metrics.incr("cache.subtree.miss")
        visited: set[str] = set()
        results: List[str] = []
        queue: deque[Tuple[str, int]] = deque([(concept_id, 0)])
        size_limit = self.config.max_subtree_size
        depth_limit = max_depth

        while queue and len(results) < size_limit:
            node, depth = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            results.append(node)
            if depth_limit is not None and depth >= depth_limit:
                continue
            for child in self.list_children(node):
                if child not in visited:
                    queue.append((child, depth + 1))

        frozen = tuple(results)
        self._subtree_cache.set(cache_key, frozen)
        duration = time.perf_counter() - start
        self.metrics.observe("query.subtree.duration_seconds", duration)
        return list(frozen)

    # ------------------------------------------------------------------
    # SPARQL gateway
    # ------------------------------------------------------------------
    def sparql_query(
        self,
        endpoint_url: str,
        query_text: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[Dict[str, str]] = None,
        snapshot_version: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, object]:
        self._validate_sparql_query(query_text)
        self._validate_sparql_endpoint(endpoint_url)
        self.metrics.incr("sparql.requests")

        cache_key = self._cache_key(endpoint_url, query_text, headers, auth, snapshot_version)
        now = time.time()
        cached = self._sparql_cache.get(cache_key)
        if cached and not force_refresh:
            if now - cached["timestamp"] <= self.config.sparql_cache_ttl_seconds:
                self._record_sparql_metric(cache_hit=True)
                self.metrics.incr("sparql.cache_hit")
                self.metrics.observe("sparql.duration_seconds", 0.0)
                return {
                    "from_cache": True,
                    "result": cached["result"],
                    "duration_seconds": cached.get("duration", 0.0),
                }
            # expired cache entry
            del self._sparql_cache[cache_key]

        self.metrics.incr("sparql.cache_miss")

        client = SPARQLWrapper(endpoint_url)
        client.setReturnFormat(SPARQL_JSON)
        client.setTimeout(self.config.sparql_timeout_seconds)
        if headers:
            for key, value in headers.items():
                client.addCustomHttpHeader(key, value)
        if auth and "Authorization" in auth:
            client.addCustomHttpHeader("Authorization", auth["Authorization"])

        client.setQuery(query_text)

        start = time.perf_counter()
        try:
            result = client.query().convert()
        except Exception as exc:  # noqa: BLE001
            self._record_sparql_metric(cache_hit=False, error=True)
            self.metrics.incr("sparql.errors")
            logger.exception("SPARQL query failed: %s", exc)
            raise
        duration = time.perf_counter() - start
        logger.debug("SPARQL query executed in %.3fs", duration)
        self.metrics.observe("sparql.duration_seconds", duration)

        if "results" in result and "bindings" in result["results"]:
            bindings = result["results"]["bindings"]
            if len(bindings) > self.config.sparql_max_rows:
                bindings = bindings[: self.config.sparql_max_rows]
                result["results"]["bindings"] = bindings

        self._sparql_cache[cache_key] = {
            "result": result,
            "timestamp": now,
            "duration": duration,
        }
        self._record_sparql_metric(cache_hit=False, duration=duration)
        return {
            "from_cache": False,
            "result": result,
            "duration_seconds": duration,
        }

    def _cache_key(
        self,
        endpoint_url: str,
        query_text: str,
        headers: Optional[Dict[str, str]],
        auth: Optional[Dict[str, str]],
        snapshot_version: Optional[str],
    ) -> str:
        serializable_headers = tuple(sorted((headers or {}).items()))
        serializable_auth = tuple(sorted((auth or {}).items()))
        return f"{endpoint_url}|{query_text}|{serializable_headers}|{serializable_auth}|{snapshot_version or ''}"

    def _validate_sparql_query(self, query_text: str) -> None:
        normalized = query_text.strip().upper()
        if not any(normalized.startswith(prefix) for prefix in self.config.sparql_allowed_starts):
            raise ValueError("Unsupported SPARQL operation; only read queries are permitted")
        for keyword in self.config.sparql_disallowed_keywords:
            if keyword in normalized:
                raise ValueError(f"Disallowed SPARQL keyword detected: {keyword}")

    def _validate_sparql_endpoint(self, endpoint_url: str) -> None:
        if not self.config.sparql_allowed_endpoints:
            return
        if not any(endpoint_url.startswith(prefix) for prefix in self.config.sparql_allowed_endpoints):
            raise ValueError(f"Endpoint not allowed for SPARQL gateway: {endpoint_url}")

    def _record_sparql_metric(self, *, cache_hit: bool, error: bool = False, duration: float = 0.0) -> None:
        self.sparql_metrics["total"] = int(self.sparql_metrics.get("total", 0)) + 1
        if cache_hit:
            self.sparql_metrics["cache_hits"] = int(self.sparql_metrics.get("cache_hits", 0)) + 1
        else:
            self.sparql_metrics["cache_misses"] = int(self.sparql_metrics.get("cache_misses", 0)) + 1
        if error:
            self.sparql_metrics["errors"] = int(self.sparql_metrics.get("errors", 0)) + 1
        else:
            durations: List[float] = list(self.sparql_metrics.get("durations", []))
            durations.append(duration)
            self.sparql_metrics["durations"] = durations

    # ------------------------------------------------------------------
    # Fuzzy search
    # ------------------------------------------------------------------
    def search_labels(
        self,
        query: str,
        *,
        lang: Optional[str] = None,
        limit: Optional[int] = None,
        score_cutoff: Optional[float] = None,
        use_semantic: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        self.metrics.incr("query.search.requests")

        if limit is None:
            limit = self.config.fuzzy_match_limit
        if score_cutoff is None:
            score_cutoff = self.config.fuzzy_score_cutoff
        semantic_enabled = self.config.enable_semantic_fallback if use_semantic is None else use_semantic

        cache_key = (query.strip().lower(), lang, limit, score_cutoff, semantic_enabled)
        start = time.perf_counter()
        cached = self._label_search_cache.get(cache_key)
        if cached is not None:
            self.metrics.incr("cache.search.hit")
            duration = time.perf_counter() - start
            self.metrics.observe("query.search.duration_seconds", duration)
            return _thaw_records(cached)

        self.metrics.incr("cache.search.miss")

        label_df = self.tables.labels
        if lang:
            label_df = label_df[label_df["language"].fillna("") == lang]

        labels = label_df["text"].astype(str).tolist()
        matches = process.extract(
            query,
            labels,
            score_cutoff=score_cutoff,
            limit=limit,
        )

        results: List[Dict[str, Any]] = []
        seen_concepts: set[Optional[str]] = set()
        for label_text, score, idx in matches:
            row = label_df.iloc[idx]
            concept_id = row.get("concept_id")
            seen_concepts.add(concept_id)
            results.append(
                {
                    "concept_id": concept_id,
                    "label": label_text,
                    "score": score,
                    "language": row.get("language"),
                    "is_preferred": row.get("is_preferred"),
                    "kind": row.get("kind"),
                    "retrieval": "fuzzy",
                    "non_authoritative": False,
                }
            )

        if (
            semantic_enabled
            and self.semantic_index is not None
            and len(results) < limit
        ):
            semantic_results = self.semantic_index.search(query, lang=lang, limit=limit)
            if semantic_results:
                self.metrics.incr("query.search.semantic_requests")
            for item in semantic_results:
                concept_id = item.get("concept_id")
                if concept_id in seen_concepts:
                    continue
                enriched: Dict[str, Any] = {
                    "concept_id": concept_id,
                    "label": item.get("label"),
                    "score": item.get("score"),
                    "language": item.get("language", lang),
                    "retrieval": "semantic",
                    "non_authoritative": True,
                }
                for key, value in item.items():
                    enriched.setdefault(key, value)
                results.append(enriched)
                seen_concepts.add(concept_id)
                if len(results) >= limit:
                    break

        results = results[:limit]
        frozen = _freeze_records(results)
        self._label_search_cache.set(cache_key, frozen)
        duration = time.perf_counter() - start
        self.metrics.observe("query.search.duration_seconds", duration)
        return results

    # ------------------------------------------------------------------
    # Internal relation cache
    # ------------------------------------------------------------------
    @property
    def _relations(self) -> "RelationCache":
        if not hasattr(self, "__relation_cache"):
            self.__relation_cache = RelationCache(
                self.tables.relations,
                cache_size=self.config.relation_cache_size,
                metrics=self.metrics,
            )
        return self.__relation_cache


class RelationCache:
    """LRU-backed access to relation fan-out lists."""

    def __init__(
        self,
        relations_df: pd.DataFrame,
        *,
        cache_size: int = 256,
        metrics: Optional[QueryMetrics] = None,
    ) -> None:
        self._relations_df = relations_df
        self._cache: LRUCache[Tuple[str, str], Tuple[str, ...]] = LRUCache(cache_size)
        self._metrics = metrics

    def get(self, predicate: str, concept_id: str) -> List[str]:
        key = (predicate, concept_id)
        cached = self._cache.get(key)
        if cached is not None:
            if self._metrics:
                self._metrics.incr("cache.relation.hit")
            return list(cached)

        if self._metrics:
            self._metrics.incr("cache.relation.miss")

        if self._relations_df.empty or "subject_id" not in self._relations_df.columns:
            values: Tuple[str, ...] = tuple()
        else:
            subset = self._relations_df[
                (self._relations_df["subject_id"] == concept_id)
                & (self._relations_df["predicate"] == predicate)
            ]
            values = tuple(subset["object_id"].tolist())

        self._cache.set(key, values)
        return list(values)
