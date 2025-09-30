"""In-memory registry implementation for tests and examples."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from .jobs import JobRecord, JobRequest, JobStatus, Registry


@dataclass
class ArtifactEntry:
    artifact_id: str
    name: str
    type: str
    metadata: Dict[str, str]
    created_at: datetime
    updated_at: datetime
    content: Optional[bytes] = None
    content_type: str = "application/octet-stream"


class InMemoryRegistry(Registry):
    """Simple in-memory registry primarily for unit tests."""

    def __init__(self) -> None:
        self.artifacts: Dict[str, ArtifactEntry] = {}
        self.jobs: Dict[str, JobRecord] = {}
        self._quota_limits: Dict[str, Dict[str, int]] = {}
        self._quota_usage: Dict[str, Dict[str, int]] = {}
        self._job_logs: Dict[str, List[str]] = {}

    # Artifact operations -------------------------------------------------
    def create_artifact(self, payload):
        artifact_id = f"artifact-{len(self.artifacts)+1}"
        now = datetime.now(timezone.utc)
        content_bytes = payload.content.encode("utf-8") if getattr(payload, "content", None) else None
        content_type = getattr(payload, "content_type", None) or "application/octet-stream"
        entry = ArtifactEntry(
            artifact_id=artifact_id,
            name=payload.name,
            type=payload.type,
            metadata=payload.metadata or {},
            created_at=now,
            updated_at=now,
            content=content_bytes,
            content_type=content_type,
        )
        self.artifacts[artifact_id] = entry
        return artifact_id

    def get_artifact(self, artifact_id: str) -> ArtifactEntry:
        return self.artifacts[artifact_id]

    def update_artifact(
        self,
        artifact_id: str,
        metadata: Dict[str, str],
        *,
        content: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> None:
        entry = self.artifacts[artifact_id]
        entry.metadata = metadata
        entry.updated_at = datetime.now(timezone.utc)
        if content is not None:
            entry.content = content.encode("utf-8")
        if content_type is not None:
            entry.content_type = content_type

    def delete_artifact(self, artifact_id: str) -> None:
        self.artifacts.pop(artifact_id, None)

    def list_artifacts(self) -> Iterable[ArtifactEntry]:
        return list(self.artifacts.values())

    def get_artifact_payload(self, artifact_id: str) -> tuple[Optional[bytes], str]:
        entry = self.artifacts[artifact_id]
        return entry.content, entry.content_type

    # Job operations ------------------------------------------------------
    def enqueue_job(self, request: JobRequest) -> JobRecord:
        job_id = f"job-{len(self.jobs)+1}"
        now = datetime.now(timezone.utc)
        record = JobRecord(
            job_id=job_id,
            status=JobStatus.QUEUED,
            request=request,
            submitted_at=now,
            updated_at=now,
        )
        self.jobs[job_id] = record
        self._increment_quota(request.tenant, request.job_type)
        self._job_logs[job_id] = [
            json.dumps(
                {
                    "event": "queued",
                    "job_id": job_id,
                    "job_type": request.job_type,
                    "tenant": request.tenant,
                    "project": request.project,
                },
                sort_keys=True,
            )
        ]
        return record

    def get_job(self, job_id: str) -> JobRecord:
        return self.jobs[job_id]

    def list_jobs(self, tenant: Optional[str] = None) -> Iterable[JobRecord]:
        records: List[JobRecord] = list(self.jobs.values())
        if tenant is None:
            return records
        return [record for record in records if record.request.tenant == tenant]

    def stream_logs(self, job_id: str):  # pragma: no cover - trivial generator
        for line in self._job_logs.get(job_id, []):
            yield line

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        log_pointer: Optional[str] = None,
        retries: Optional[int] = None,
    ) -> None:
        record = self.jobs[job_id]
        record.status = status
        record.updated_at = datetime.now(timezone.utc)
        if log_pointer is not None:
            record.log_pointer = log_pointer
            self._job_logs.setdefault(job_id, []).append(log_pointer)
        if retries is not None:
            record.retries = retries
        self._job_logs.setdefault(job_id, []).append(
            json.dumps(
                {
                    "event": "status",
                    "status": status,
                    "job_id": job_id,
                    "retries": record.retries,
                },
                sort_keys=True,
            )
        )

    # Quota helpers -------------------------------------------------------
    def quota_usage(self, tenant: str) -> Dict[str, int]:
        return dict(self._quota_usage.get(tenant, {}))

    def quota_limits(self, tenant: str) -> Dict[str, int]:
        return dict(self._quota_limits.get(tenant, {}))

    def set_quota(self, tenant: str, quota_type: str, limit: int) -> None:
        self._quota_limits.setdefault(tenant, {})[quota_type] = limit

    def _increment_quota(self, tenant: str, quota_type: str) -> None:
        tenant_usage = self._quota_usage.setdefault(tenant, {})
        tenant_usage[quota_type] = tenant_usage.get(quota_type, 0) + 1
