#!/usr/bin/env python3
"""Prepare Qwen3 checkpoints for TensorRT-LLM conversion."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Qwen3 checkpoints for TRT-LLM")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "checkpoint.json").write_text("{}", encoding="utf-8")


if __name__ == "__main__":
    main()
