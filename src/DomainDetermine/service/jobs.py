"""Job orchestration primitives for the service layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Iterable, Optional


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class JobRequest:
    job_type: str
    payload: Dict[str, str]
    tenant: str
    project: str
    actor: str
    reason: str


@dataclass
class JobRecord:
    job_id: str
    status: JobStatus
    request: JobRequest
    submitted_at: datetime
    updated_at: datetime
    retries: int = 0
    log_pointer: Optional[str] = None


class Registry:
    """Registry interface expected by the service layer."""

    def create_artifact(self, payload):  # pragma: no cover - placeholder
        raise NotImplementedError

    def get_artifact(self, artifact_id: str):  # pragma: no cover - placeholder
        raise NotImplementedError

    def update_artifact(self, artifact_id: str, metadata: Dict[str, str]):  # pragma: no cover
        raise NotImplementedError

    def delete_artifact(self, artifact_id: str):  # pragma: no cover - placeholder
        raise NotImplementedError

    def list_artifacts(self):  # pragma: no cover - placeholder
        raise NotImplementedError

    def enqueue_job(self, request: JobRequest) -> JobRecord:  # pragma: no cover - placeholder
        raise NotImplementedError

    def get_job(self, job_id: str) -> JobRecord:  # pragma: no cover - placeholder
        raise NotImplementedError

    def list_jobs(self, tenant: Optional[str] = None):  # pragma: no cover - placeholder
        raise NotImplementedError

    def stream_logs(self, job_id: str):  # pragma: no cover - placeholder
        raise NotImplementedError

    def quota_usage(self, tenant: str) -> Dict[str, int]:  # pragma: no cover - placeholder
        raise NotImplementedError

    def quota_limits(self, tenant: str) -> Dict[str, int]:  # pragma: no cover - placeholder
        raise NotImplementedError


@dataclass
class QuotaManager:
    registry: Registry
    window: timedelta = field(default=timedelta(days=1))

    def check(self, tenant: str, quota_type: str, increment: int = 1) -> None:
        limits = self.registry.quota_limits(tenant)
        usage = self.registry.quota_usage(tenant)
        limit = limits.get(quota_type)
        if limit is None:
            return
        if usage.get(quota_type, 0) + increment > limit:
            raise QuotaExceededError(quota_type, limit, usage.get(quota_type, 0))


class QuotaExceededError(RuntimeError):
    def __init__(self, quota_type: str, limit: int, used: int) -> None:
        super().__init__(f"Quota exceeded for {quota_type}: {used}/{limit}")
        self.quota_type = quota_type
        self.limit = limit
        self.used = used


@dataclass
class JobManager:
    registry: Registry
    quota_manager: Optional[QuotaManager] = None

    def enqueue(self, request: JobRequest) -> JobRecord:
        if self.quota_manager is None:
            self.quota_manager = QuotaManager(self.registry)
        self.quota_manager.check(request.tenant, request.job_type)
        return self.registry.enqueue_job(request)

    def get(self, job_id: str) -> JobRecord:
        return self.registry.get_job(job_id)

    def list(self, tenant: Optional[str] = None) -> Iterable[JobRecord]:
        return self.registry.list_jobs(tenant)

    def stream_logs(self, job_id: str):
        return self.registry.stream_logs(job_id)

