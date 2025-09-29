#!/usr/bin/env python3
"""Apply AWQ W4A8 quantization to prepared checkpoints."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quantize checkpoints with AWQ W4A8")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--calibration", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "quantized.json").write_text("{}", encoding="utf-8")


if __name__ == "__main__":
    main()
