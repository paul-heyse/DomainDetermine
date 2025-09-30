"""Calibration assets and manifests for prompt templates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Sequence


@dataclass(frozen=True)
class CalibrationExample:
    """Represents a single calibration example for a prompt template."""

    input_payload: Mapping[str, object]
    expected_output: Mapping[str, object]
    notes: str = ""


@dataclass(frozen=True)
class CalibrationSet:
    """Collection of calibration examples for a template."""

    template_id: str
    version: str
    examples: Sequence[CalibrationExample] = field(default_factory=tuple)

    def __iter__(self) -> Iterable[CalibrationExample]:
        return iter(self.examples)


@dataclass(frozen=True)
class CalibrationManifest:
    """Metadata describing a calibration dataset and its provenance."""

    template_id: str
    version: str
    dataset_path: Path
    reviewers: Sequence[str]
    approvals: Sequence[str]
    checksum: str
    license_tag: str
    last_reviewed_at: datetime
    provenance: Mapping[str, object] = field(default_factory=dict)

    def verify(self) -> None:
        """Validate dataset presence and checksum before use."""

        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Calibration dataset not found at {self.dataset_path}",
            )
        digest = hashlib.sha256(self.dataset_path.read_bytes()).hexdigest()
        if digest != self.checksum:
            raise ValueError(
                "Calibration dataset checksum mismatch",
            )
        if not self.reviewers:
            raise ValueError("Calibration manifest must list at least one reviewer")
        if not self.approvals:
            raise ValueError("Calibration manifest must include approvals")


@dataclass(frozen=True)
class CalibrationDataset:
    """Aggregated calibration manifest and examples."""

    manifest: CalibrationManifest
    calibration_set: CalibrationSet


CALIBRATION_DATASETS: MutableMapping[tuple[str, str], CalibrationDataset] = {}


def _default_calibration_root() -> Path:
    return Path(__file__).resolve().parents[3] / "docs" / "prompt_pack" / "calibration"


def load_calibration_manifest(
    template_id: str,
    version: str,
    *,
    root: Path | None = None,
) -> CalibrationManifest:
    """Load and validate a calibration manifest from disk."""

    base = (root or _default_calibration_root()) / template_id / version
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Calibration manifest not found at {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    dataset_rel = payload.get("dataset_path")
    if not dataset_rel:
        raise ValueError("Calibration manifest missing 'dataset_path'")
    last_reviewed = payload.get("last_reviewed_at")
    if not last_reviewed:
        raise ValueError("Calibration manifest missing 'last_reviewed_at'")
    manifest = CalibrationManifest(
        template_id=payload.get("template_id", template_id),
        version=payload.get("version", version),
        dataset_path=(base / dataset_rel).resolve(),
        reviewers=tuple(payload.get("reviewers", ())),
        approvals=tuple(payload.get("approvals", ())),
        checksum=payload.get("checksum", ""),
        license_tag=payload.get("license", "internal"),
        last_reviewed_at=datetime.fromisoformat(last_reviewed),
        provenance=payload.get("provenance", {}),
    )
    manifest.verify()
    return manifest


def _load_examples(dataset_path: Path) -> Sequence[CalibrationExample]:
    examples: list[CalibrationExample] = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        examples.append(
            CalibrationExample(
                input_payload=record["input_payload"],
                expected_output=record["expected_output"],
                notes=record.get("notes", ""),
            ),
        )
    return tuple(examples)


def load_calibration_dataset(
    template_id: str,
    version: str,
    *,
    root: Path | None = None,
) -> CalibrationDataset:
    """Load calibration manifest and dataset for a template/version."""

    key = (template_id, version)
    if key in CALIBRATION_DATASETS:
        return CALIBRATION_DATASETS[key]
    manifest = load_calibration_manifest(template_id, version, root=root)
    examples = _load_examples(manifest.dataset_path)
    calibration_set = CalibrationSet(
        template_id=manifest.template_id,
        version=manifest.version,
        examples=examples,
    )
    dataset = CalibrationDataset(manifest=manifest, calibration_set=calibration_set)
    CALIBRATION_DATASETS[key] = dataset
    return dataset


def register_calibration_dataset(dataset: CalibrationDataset) -> None:
    """Register a dataset instance for quick retrieval without disk access."""

    key = (dataset.calibration_set.template_id, dataset.calibration_set.version)
    CALIBRATION_DATASETS[key] = dataset


def get_calibration_set(template_id: str, version: str) -> CalibrationSet:
    """Fetch a calibration set for the provided template/version."""

    dataset = load_calibration_dataset(template_id, version)
    return dataset.calibration_set


# Eagerly load default calibration assets shipped with the repository.
try:
    register_calibration_dataset(load_calibration_dataset("mapping_decision", "1.0.0"))
except (FileNotFoundError, ValueError):  # pragma: no cover - optional bootstrap
    pass


__all__ = [
    "CalibrationDataset",
    "CalibrationExample",
    "CalibrationManifest",
    "CalibrationSet",
    "get_calibration_set",
    "load_calibration_dataset",
    "load_calibration_manifest",
]
