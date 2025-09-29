"""Persistence helpers for coverage auditor artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

from DomainDetermine.auditor.models import AuditArtifactPaths, AuditCertificate


class AuditStorage:
    """Stores audit datasets, certificates, reports, and assets under an immutable root."""

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path
        self._base_path.mkdir(parents=True, exist_ok=True)

    @property
    def base_path(self) -> Path:
        return self._base_path

    def _resolve(self, relative_path: str) -> Path:
        path = self._base_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def write_dataset(self, records: Sequence[Mapping[str, object]], *, relative_path: str) -> None:
        path = self._resolve(relative_path)
        payload = [dict(record) for record in records]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    def write_certificate(self, certificate: AuditCertificate, *, relative_path: str) -> None:
        path = self._resolve(relative_path)
        data = {
            "metadata": dict(certificate.metadata),
            "metrics": [
                {
                    "name": metric.name,
                    "value": metric.value,
                    "threshold": metric.threshold,
                    "comparator": metric.comparator,
                    "status": metric.status.value,
                    "gate_level": metric.gate_level.value,
                    "rationale": metric.rationale,
                    "owner": metric.owner,
                    "extra": dict(metric.extra),
                }
                for metric in certificate.metrics
            ],
            "findings_summary": dict(certificate.findings_summary),
            "waivers": [dict(waiver) for waiver in certificate.waivers],
            "signature": certificate.signature,
        }
        path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def write_report(self, report: Mapping[str, object], *, relative_path: str) -> None:
        path = self._resolve(relative_path)
        path.write_text(json.dumps(report, indent=2, sort_keys=True))

    def write_assets(self, assets: Sequence[Mapping[str, object]]) -> Sequence[str]:
        stored_paths: list[str] = []
        for asset in assets:
            relative_path = str(asset.get("path"))
            content = asset.get("content")
            path = self._resolve(relative_path)
            if isinstance(content, (Mapping, list, tuple)):
                path.write_text(json.dumps(content, indent=2, sort_keys=True))
            else:
                path.write_text(str(content))
            stored_paths.append(relative_path)
        return tuple(stored_paths)

    def persist_all(
        self,
        *,
        dataset: Sequence[Mapping[str, object]],
        certificate: AuditCertificate,
        report: Mapping[str, object],
        artifact_paths: AuditArtifactPaths,
        assets: Sequence[Mapping[str, object]],
    ) -> AuditArtifactPaths:
        self.write_dataset(dataset, relative_path=artifact_paths.dataset_uri)
        self.write_certificate(certificate, relative_path=artifact_paths.certificate_uri)
        self.write_report(report, relative_path=artifact_paths.report_uri)
        stored_assets = self.write_assets(assets)
        return AuditArtifactPaths(
            dataset_uri=artifact_paths.dataset_uri,
            certificate_uri=artifact_paths.certificate_uri,
            report_uri=artifact_paths.report_uri,
            assets=stored_assets,
        )


__all__ = ["AuditStorage"]
