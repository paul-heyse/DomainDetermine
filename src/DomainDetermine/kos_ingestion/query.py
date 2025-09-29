"""Query service for KOS snapshots."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Sequence

import duckdb
import pandas as pd
from rapidfuzz import process
from SPARQLWrapper import JSON as SPARQL_JSON
from SPARQLWrapper import SPARQLWrapper

from .canonical import SnapshotTables

logger = logging.getLogger(__name__)


@dataclass
class QueryConfig:
    max_subtree_size: int = 5000
    cache_size: int = 256
    fuzzy_match_limit: int = 25
    fuzzy_score_cutoff: float = 70.0
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


class SnapshotQueryService:
    """Provides read APIs over `SnapshotTables` with caching and DuckDB.

    The service is constructed from a `SnapshotTables` instance and maintains
    in-process DuckDB connections for analytics-oriented queries while offering
    high-level traversal helpers based on pandas DataFrames.
    """

    def __init__(self, tables: SnapshotTables, *, config: Optional[QueryConfig] = None) -> None:
        self.tables = tables
        self.config = config or QueryConfig()
        self._duckdb = duckdb.connect(database=":memory:")
        self._register_tables()
        self._sparql_cache: Dict[str, Dict[str, object]] = {}
        self.sparql_metrics: Dict[str, object] = {
            "total": 0,
            "cache_hits": 0,
            "errors": 0,
            "durations": [],
        }

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
    def get_concept(self, identifier: str) -> Optional[Dict[str, object]]:
        """Return the canonical concept row with labels/mappings/provenance."""

        concept = self.tables.concepts[self.tables.concepts["canonical_id"] == identifier]
        if concept.empty:
            concept = self.tables.concepts[self.tables.concepts["source_id"] == identifier]
        if concept.empty:
            return None
        concept_row = concept.iloc[0].to_dict()
        concept_row["labels"] = self._labels_for_concept(concept_row["canonical_id"])
        concept_row["mappings"] = self._mappings_for_concept(concept_row["canonical_id"])
        concept_row["relations"] = self._relations_for_concept(concept_row["canonical_id"])
        return concept_row

    def _labels_for_concept(self, concept_id: str) -> List[Dict[str, object]]:
        subset = self.tables.labels[self.tables.labels["concept_id"] == concept_id]
        return subset.to_dict(orient="records")

    def _mappings_for_concept(self, concept_id: str) -> List[Dict[str, object]]:
        if "subject_id" not in self.tables.mappings.columns:
            return []
        subset = self.tables.mappings[self.tables.mappings["subject_id"] == concept_id]
        return subset.to_dict(orient="records")

    def _relations_for_concept(self, concept_id: str) -> Dict[str, List[str]]:
        if "subject_id" not in self.tables.relations.columns:
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
        limit = max_depth or self.config.max_subtree_size
        results: List[str] = []
        queue: List[tuple[str, int]] = [(concept_id, 0)]
        visited: set[str] = set()
        while queue and len(results) < self.config.max_subtree_size:
            node, depth = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            results.append(node)
            if depth >= limit:
                continue
            for child in self.list_children(node):
                queue.append((child, depth + 1))
        return results

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

        cache_key = self._cache_key(endpoint_url, query_text, headers, auth, snapshot_version)
        now = time.time()
        cached = self._sparql_cache.get(cache_key)
        if cached and not force_refresh:
            if now - cached["timestamp"] <= self.config.sparql_cache_ttl_seconds:
                self._record_sparql_metric(cache_hit=True)
                return {
                    "from_cache": True,
                    "result": cached["result"],
                    "duration_seconds": cached.get("duration", 0.0),
                }
            # expired cache entry
            del self._sparql_cache[cache_key]

        client = SPARQLWrapper(endpoint_url)
        client.setReturnFormat(SPARQL_JSON)
        client.setTimeout(self.config.sparql_timeout_seconds)
        if headers:
            for key, value in headers.items():
                client.addCustomHttpHeader(key, value)
        if auth and "Authorization" in auth:
            client.addCustomHttpHeader("Authorization", auth["Authorization"])

        client.setQuery(query_text)

        start = time.time()
        try:
            result = client.query().convert()
        except Exception as exc:  # noqa: BLE001
            self._record_sparql_metric(cache_hit=False, error=True)
            logger.exception("SPARQL query failed: %s", exc)
            raise
        duration = time.time() - start
        logger.debug("SPARQL query executed in %.3fs", duration)

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

    def _record_sparql_metric(self, *, cache_hit: bool, error: bool = False, duration: float = 0.0) -> None:
        self.sparql_metrics["total"] = int(self.sparql_metrics.get("total", 0)) + 1
        if cache_hit:
            self.sparql_metrics["cache_hits"] = int(self.sparql_metrics.get("cache_hits", 0)) + 1
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
    ) -> List[Dict[str, object]]:
        if limit is None:
            limit = self.config.fuzzy_match_limit
        if score_cutoff is None:
            score_cutoff = self.config.fuzzy_score_cutoff

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

        results: List[Dict[str, object]] = []
        for label_text, score, idx in matches:
            row = label_df.iloc[idx]
            results.append(
                {
                    "concept_id": row["concept_id"],
                    "label": label_text,
                    "score": score,
                    "language": row.get("language"),
                    "is_preferred": row.get("is_preferred"),
                    "kind": row.get("kind"),
                }
            )
        return results

    # ------------------------------------------------------------------
    # Internal relation cache
    # ------------------------------------------------------------------
    @property
    def _relations(self) -> "RelationCache":
        if not hasattr(self, "__relation_cache"):
            self.__relation_cache = RelationCache(self.tables.relations, cache_size=self.config.cache_size)
        return self.__relation_cache


class RelationCache:
    """LRU-backed access to relation fan-out lists."""

    def __init__(self, relations_df: pd.DataFrame, *, cache_size: int = 256) -> None:
        self._relations_df = relations_df
        self._cache_size = cache_size

    def get(self, predicate: str, concept_id: str) -> List[str]:
        return self._load(predicate, concept_id)

    @lru_cache(maxsize=256)
    def _load(self, predicate: str, concept_id: str) -> List[str]:
        subset = self._relations_df[
            (self._relations_df["subject_id"] == concept_id)
            & (self._relations_df["predicate"] == predicate)
        ]
        return subset["object_id"].tolist()

