#!/usr/bin/env python3
"""Write engine build manifests."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write engine build manifest")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--engine", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = {
        "engine": str(args.engine),
        "engine_hash": "sha256-placeholder",
        "build_started_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "build_completed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
