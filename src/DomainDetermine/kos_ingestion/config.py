"""Configuration helpers for connector profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Mapping

from .models import DeltaStrategy, ExportMode, LicensingPolicy, SourceConfig, SourceType


def load_source_configs(path: Path) -> List[SourceConfig]:
    """Load source configurations from a JSON file."""

    data = json.loads(path.read_text())
    configs = []
    for entry in data:
        configs.append(
            SourceConfig(
                id=entry["id"],
                type=SourceType(entry["type"]),
                location=entry["location"],
                format=entry.get("format"),
                license_name=entry.get("license_name", "default"),
                headers=entry.get("headers", {}),
                auth=entry.get("auth"),
                credential_secret=entry.get("credential_secret"),
                sparql_query=entry.get("sparql_query"),
                timeout_seconds=entry.get("timeout_seconds", 30),
                sparql_page_size=entry.get("sparql_page_size", 1000),
                sparql_max_rows=entry.get("sparql_max_rows", 5000),
                verify_tls=entry.get("verify_tls", True),
                max_bytes=entry.get("max_bytes"),
                resume_download=entry.get("resume_download", False),
                rate_limit_per_second=entry.get("rate_limit_per_second"),
                retry_limit=entry.get("retry_limit", 3),
                backoff_seconds=entry.get("backoff_seconds", 2.0),
                cache_ttl_seconds=entry.get("cache_ttl_seconds"),
                delta_strategy=DeltaStrategy(entry.get("delta_strategy", "etag")),
                export_mode=ExportMode(entry.get("export_mode", "full")),
            )
        )
    return configs


def load_policies(path: Path) -> Mapping[str, LicensingPolicy]:
    """Load licensing policies from a JSON file."""

    data = json.loads(path.read_text())
    policies = {}
    for entry in data:
        policies[entry["name"]] = LicensingPolicy(
            name=entry["name"],
            allow_raw_exports=entry.get("allow_raw_exports", True),
            restricted_fields=set(entry.get("restricted_fields", [])),
            notes=entry.get("notes"),
        )
    return policies
