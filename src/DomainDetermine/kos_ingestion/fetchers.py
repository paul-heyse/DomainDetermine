"""Fetch utilities for KOS ingestion connectors."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Dict, Optional

import requests
from requests import Session
from SPARQLWrapper import JSON as SPARQL_JSON
from SPARQLWrapper import SPARQLExceptions, SPARQLWrapper

from .models import (
    ConnectorContext,
    ConnectorMetadata,
    SourceConfig,
    SourceType,
)

HTTP_TIMEOUT = 30
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

logger = logging.getLogger(__name__)


class FetchError(RuntimeError):
    """Raised when a remote resource cannot be fetched."""


@dataclass
class CheckedResponse:
    """Holds a verified HTTP response and associated metadata."""

    content: bytes
    status_code: int
    headers: Dict[str, str]

    @property
    def etag(self) -> Optional[str]:
        return self.headers.get("ETag")

    @property
    def last_modified(self) -> Optional[str]:
        return self.headers.get("Last-Modified")

    def checksum(self, algorithm: str = "sha256") -> str:
        digest = hashlib.new(algorithm)
        digest.update(self.content)
        return digest.hexdigest()


class HttpFetcher:
    """HTTP/HTTPS fetcher with retry, checksum, caching, and metadata capture."""

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session or requests.Session()
        self._cache: Dict[str, tuple[float, CheckedResponse]] = {}

    def fetch(self, config: SourceConfig, context: ConnectorContext) -> CheckedResponse:
        if not config.is_remote():
            raise FetchError("HTTP fetcher can only handle remote sources")

        request_headers = dict(config.headers)
        auth_headers = config.auth_headers(context)
        if auth_headers:
            request_headers.update(auth_headers)

        url = config.location
        attempt = 0
        backoff = config.backoff_seconds
        cache_key = None
        if config.cache_ttl_seconds:
            cache_key = json.dumps(
                {
                    "url": url,
                    "headers": request_headers,
                },
                sort_keys=True,
            )
            cached = self._cache.get(cache_key)
            if cached:
                cached_ts, cached_response = cached
                if time.time() - cached_ts < config.cache_ttl_seconds:
                    logger.debug("HTTP cache hit for %s", url)
                    return CheckedResponse(
                        content=cached_response.content,
                        status_code=cached_response.status_code,
                        headers=dict(cached_response.headers),
                    )
        if config.rate_limit_per_second:
            self._respect_rate_limit(config, context)
        while True:
            attempt += 1
            try:
                logger.debug("Fetching URL %s (attempt %s)", url, attempt)
                response = self._session.get(
                    url,
                    headers=request_headers,
                    timeout=config.timeout_seconds or HTTP_TIMEOUT,
                    verify=config.verify_tls,
                    stream=config.resume_download,
                )
            except requests.RequestException as exc:
                if attempt > config.retry_limit:
                    raise FetchError(f"Failed to fetch {url}: {exc}") from exc
                logger.warning("HTTP fetch error (attempt %s/%s): %s", attempt, config.retry_limit, exc)
                time.sleep(backoff * attempt)
                continue

            if response.status_code in RETRYABLE_STATUS and attempt <= config.retry_limit:
                logger.warning(
                    "Retryable status %s for %s (attempt %s/%s)",
                    response.status_code,
                    url,
                    attempt,
                    config.retry_limit,
                )
                time.sleep(backoff * attempt)
                continue

            if response.status_code >= 400:
                raise FetchError(f"Failed to fetch {url}: HTTP {response.status_code}")

            content = response.content
            if config.max_bytes and len(content) > config.max_bytes:
                raise FetchError(f"Response too large ({len(content)} bytes > {config.max_bytes}) for {url}")

            checked = CheckedResponse(
                content=content,
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items()},
            )
            if cache_key and config.cache_ttl_seconds:
                self._cache[cache_key] = (time.time(), checked)
            return checked

    def _respect_rate_limit(self, config: SourceConfig, context: ConnectorContext) -> None:
        key = context.throttle_key(config)
        last_call = context.rate_limit_state.get(key)
        min_interval = 1.0 / config.rate_limit_per_second
        if last_call is not None:
            elapsed = time.time() - last_call
            wait_for = min_interval - elapsed
            if wait_for > 0:
                logger.debug("Throttling request to %s for %.3fs", config.location, wait_for)
                time.sleep(wait_for)
        context.rate_limit_state[key] = time.time()


class SparqlFetcher:
    """Executes parameterised read-only SPARQL queries with safeguards."""

    def __init__(self) -> None:
        self._cache: Dict[str, tuple[float, bytes]] = {}

    def fetch(self, config: SourceConfig, context: ConnectorContext) -> CheckedResponse:
        if config.type is not SourceType.SPARQL:
            raise FetchError("SPARQL fetcher only supports SPARQL sources")
        if not config.sparql_query:
            raise FetchError("SPARQL config must provide a query")

        cache_key = json.dumps(
            {
                "url": config.location,
                "query": config.sparql_query,
                "headers": dict(config.headers),
                "auth": dict(config.auth or {}),
            },
            sort_keys=True,
        )
        cached = self._cache.get(cache_key)
        if cached and config.cache_ttl_seconds:
            cached_ts, cached_bytes = cached
            if time.time() - cached_ts < config.cache_ttl_seconds:
                logger.debug("Using cached SPARQL result for %s", config.location)
                return CheckedResponse(content=cached_bytes, status_code=200, headers={})

        client = SPARQLWrapper(config.location, agent="DomainDetermine/1.0", onlyConneg=True)
        client.setReturnFormat(SPARQL_JSON)
        if config.headers:
            for key, value in config.headers.items():
                client.addCustomHttpHeader(key, value)
        auth_headers = config.auth_headers(context)
        if auth_headers:
            for key, value in auth_headers.items():
                client.addCustomHttpHeader(key, value)

        client.setTimeout(config.timeout_seconds or HTTP_TIMEOUT)
        client.setQuery(config.sparql_query)

        try:
            result = client.queryAndConvert()
        except SPARQLExceptions.EndPointInternalError as exc:  # pragma: no cover - library behaviour
            raise FetchError(f"SPARQL endpoint error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - SPARQL client raises generic exceptions
            raise FetchError(f"SPARQL query failed: {exc}") from exc

        content = json.dumps(result).encode("utf-8")
        if config.cache_ttl_seconds:
            self._cache[cache_key] = (time.time(), content)
        return CheckedResponse(content=content, status_code=200, headers={})


def build_metadata(
    config: SourceConfig,
    context: ConnectorContext,
    response: CheckedResponse,
    bytes_downloaded: int,
    checksum: Optional[str],
    delta: str,
) -> ConnectorMetadata:
    policy = context.resolve_policy(config.license_name)
    metadata = ConnectorMetadata(
        source_id=config.id,
        source_type=config.type,
        retrieved_at=datetime.now(UTC),
        bytes_downloaded=bytes_downloaded,
        checksum=checksum,
        etag=response.etag,
        last_modified=response.last_modified,
        delta=delta,
        license_name=policy.name,
        export_allowed=policy.export_allowed(),
        restricted_fields=tuple(sorted(policy.restricted_fields)),
        policy_notes=policy.notes,
        fetch_url=config.location if config.is_remote() else None,
    )
    metadata.extra["delta_strategy"] = config.delta_strategy.value
    metadata.extra["export_mode"] = config.export_mode.value
    return metadata
