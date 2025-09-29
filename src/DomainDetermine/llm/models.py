"""Dataclasses describing LLM engine build metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class ModelSnapshot:
    """Records the upstream model artefacts used for engine builds."""

    model_id: str
    revision: str
    tokenizer_files: tuple[Path, ...]
    license_acceptance: str

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "revision": self.revision,
            "tokenizer_files": [str(path) for path in self.tokenizer_files],
            "license_acceptance": self.license_acceptance,
        }


@dataclass(frozen=True, slots=True)
class BuildFlags:
    """Captures the TensorRT-LLM build options applied."""

    use_paged_context_fmha: bool
    kv_cache_type: str
    kv_cache_precision: str
    tokens_per_block: int
    max_batch_size: int
    max_input_tokens: int
    max_output_tokens: int
    additional_args: tuple[str, ...] = ()

    def to_list(self) -> list[str]:
        flags = [
            "--use_paged_context_fmha",
            "enable" if self.use_paged_context_fmha else "disable",
            "--kv_cache_type",
            self.kv_cache_type,
            "--kv_cache_precision",
            self.kv_cache_precision,
            "--tokens_per_block",
            str(self.tokens_per_block),
            "--max_batch_size",
            str(self.max_batch_size),
            "--max_input_tokens",
            str(self.max_input_tokens),
            "--max_output_tokens",
            str(self.max_output_tokens),
        ]
        flags.extend(self.additional_args)
        return flags


@dataclass(frozen=True, slots=True)
class CalibrationDataset:
    """Represents calibration data used during quantisation."""

    name: str
    source_uri: str
    hash: str


@dataclass(frozen=True, slots=True)
class BuildManifest:
    """Immutable manifest emitted after a successful engine build."""

    snapshot: ModelSnapshot
    build_flags: BuildFlags
    calibration: CalibrationDataset
    engine_hash: str
    engine_path: Path
    build_started_at: datetime
    build_completed_at: datetime
    tool_versions: Mapping[str, str]
    smoke_tests: Sequence[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "snapshot": self.snapshot.to_dict(),
            "build_flags": self.build_flags.to_list(),
            "calibration": {
                "name": self.calibration.name,
                "source_uri": self.calibration.source_uri,
                "hash": self.calibration.hash,
            },
            "engine_hash": self.engine_hash,
            "engine_path": str(self.engine_path),
            "build_started_at": self.build_started_at.isoformat(),
            "build_completed_at": self.build_completed_at.isoformat(),
            "tool_versions": dict(self.tool_versions),
            "smoke_tests": list(self.smoke_tests),
        }
