#!/usr/bin/env python3
"""Download a Hugging Face snapshot for reproducible builds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from huggingface_hub import snapshot_download


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download HF model snapshot")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = snapshot_download(args.model_id, revision=args.revision, local_dir=args.output)
    metadata = {
        "model_id": args.model_id,
        "revision": args.revision,
        "path": path,
    }
    (args.output / "snapshot.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
