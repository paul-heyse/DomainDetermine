"""Utilities for tokenizer metadata used by guided decoding."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Optional

from transformers import AutoTokenizer


@dataclass(slots=True)
class TokenizerInfoCache:
    """Caches tokenizer info files for Triton xgrammar guided decoding."""

    tokenizer_dir: Path
    cache_dir: Optional[Path] = None

    def get_or_create(self) -> Path:
        target_dir = (self.cache_dir or self.tokenizer_dir).expanduser().resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        info_path = target_dir / "tokenizer_info.json"
        if info_path.exists():
            return info_path
        tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_dir)
        info_payload = {
            "tokenizer_hash": self._hash_dir(self.tokenizer_dir),
            "model_max_length": tokenizer.model_max_length,
            "pad_token_id": tokenizer.pad_token_id,
            "bos_token_id": tokenizer.bos_token_id,
            "eos_token_id": tokenizer.eos_token_id,
            "unk_token_id": tokenizer.unk_token_id,
        }
        info_path.write_text(json.dumps(info_payload, indent=2), encoding="utf-8")
        return info_path

    def _hash_dir(self, directory: Path) -> str:
        digest = sha256()
        for path in sorted(directory.glob("**/*")):
            if path.is_file():
                digest.update(path.name.encode("utf-8"))
                digest.update(path.read_bytes())
        return digest.hexdigest()


def generate_tokenizer_info(tokenizer_dir: Path, output: Path) -> Path:
    cache = TokenizerInfoCache(tokenizer_dir=tokenizer_dir, cache_dir=output.parent)
    info_path = cache.get_or_create()
    output.parent.mkdir(parents=True, exist_ok=True)
    if info_path != output:
        output.write_text(info_path.read_text(encoding="utf-8"), encoding="utf-8")
        return output
    return info_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate tokenizer info cache for Triton guided decoding")
    parser.add_argument("--tokenizer-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    path = generate_tokenizer_info(args.tokenizer_dir, args.output)
    print(path)
