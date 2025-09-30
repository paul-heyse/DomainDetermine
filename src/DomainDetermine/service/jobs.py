"""Job orchestration primitives for the service layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, Iterable, Optional

from DomainDetermine.governance.event_log import GovernanceEventLog, GovernanceEventType

from .events import emit_job_event
from .telemetry import job_span


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

    def update_artifact(
        self,
        artifact_id: str,
        metadata: Dict[str, str],
        *,
        content: Optional[str] = None,
        content_type: Optional[str] = None,
    ):  # pragma: no cover
        raise NotImplementedError

    def delete_artifact(self, artifact_id: str):  # pragma: no cover - placeholder
        raise NotImplementedError

    def list_artifacts(self):  # pragma: no cover - placeholder
        raise NotImplementedError

    def get_artifact_payload(self, artifact_id: str) -> tuple[Optional[bytes], str]:  # pragma: no cover
        raise NotImplementedError

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        log_pointer: Optional[str] = None,
        retries: Optional[int] = None,
    ) -> None:  # pragma: no cover - placeholder
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
        used = usage.get(quota_type, 0)
        if used + increment > limit:
            reset_in = int(self.window.total_seconds())
            raise QuotaExceededError(quota_type, limit, used, retry_after_seconds=reset_in)


class QuotaExceededError(RuntimeError):
    def __init__(self, quota_type: str, limit: int, used: int, *, retry_after_seconds: int) -> None:
        super().__init__(f"Quota exceeded for {quota_type}: {used}/{limit}")
        self.quota_type = quota_type
        self.limit = limit
        self.used = used
        self.retry_after_seconds = retry_after_seconds


@dataclass
class JobManager:
    registry: Registry
    quota_manager: Optional[QuotaManager] = None
    max_retries: int = 1
    runner: Optional["ThreadedJobRunner"] = None
    event_log: Optional[GovernanceEventLog] = None

    def enqueue(self, request: JobRequest) -> JobRecord:
        if self.quota_manager is None:
            self.quota_manager = QuotaManager(self.registry)
        if self.runner is None:
            self.runner = ThreadedJobRunner()
        self.quota_manager.check(request.tenant, request.job_type)
        record = self.registry.enqueue_job(request)
        emit_job_event(
            event_log=self.event_log,
            event_type=GovernanceEventType.SERVICE_JOB_ENQUEUED,
            job_id=record.job_id,
            tenant=request.tenant,
            actor=request.actor,
            payload={
                "job_type": request.job_type,
                "project": request.project,
            },
        )
        self.runner.submit(record, self)
        return record

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        if self.runner is None:
            self.runner = ThreadedJobRunner()
        self.runner.register_handler(job_type, handler)

    def get(self, job_id: str) -> JobRecord:
        return self.registry.get_job(job_id)

    def list(self, tenant: Optional[str] = None) -> Iterable[JobRecord]:
        return self.registry.list_jobs(tenant)

    def stream_logs(self, job_id: str):
        return self.registry.stream_logs(job_id)

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        log_pointer: Optional[str] = None,
        retries: Optional[int] = None,
    ) -> None:
        self.registry.update_job_status(
            job_id,
            status,
            log_pointer=log_pointer,
            retries=retries,
        )
        record = self.registry.get_job(job_id)
        if status == JobStatus.SUCCEEDED:
            emit_job_event(
                event_log=self.event_log,
                event_type=GovernanceEventType.SERVICE_JOB_COMPLETED,
                job_id=job_id,
                tenant=record.request.tenant,
                actor=record.request.actor,
                payload={
                    "job_type": record.request.job_type,
                    "retries": record.retries,
                    "log_pointer": log_pointer or "",
                },
            )
        elif status == JobStatus.FAILED:
            emit_job_event(
                event_log=self.event_log,
                event_type=GovernanceEventType.SERVICE_JOB_FAILED,
                job_id=job_id,
                tenant=record.request.tenant,
                actor=record.request.actor,
                payload={
                    "job_type": record.request.job_type,
                    "retries": record.retries,
                    "log_pointer": log_pointer or "",
                },
            )

    def record_failure(self, job_id: str, error: str, record: JobRecord) -> None:
        retries = record.retries + 1
        if retries <= self.max_retries:
            self.registry.update_job_status(
                job_id,
                JobStatus.QUEUED,
                log_pointer=error,
                retries=retries,
            )
            refreshed = self.registry.get_job(job_id)
            self.runner.submit(refreshed, self)
        else:
            self.registry.update_job_status(
                job_id,
                JobStatus.FAILED,
                log_pointer=error,
                retries=retries,
            )
            record = self.registry.get_job(job_id)
            emit_job_event(
                event_log=self.event_log,
                event_type=GovernanceEventType.SERVICE_JOB_FAILED,
                job_id=job_id,
                tenant=record.request.tenant,
                actor=record.request.actor,
                payload={
                    "job_type": record.request.job_type,
                    "retries": record.retries,
                    "log_pointer": error,
                },
            )


JobHandler = Callable[[JobRecord, JobManager], Optional[str]]


class ThreadedJobRunner:
    """Simple threaded job runner with optional handler registration."""

    def __init__(self, *, max_workers: int = 4) -> None:
        from concurrent.futures import ThreadPoolExecutor

        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._handlers: Dict[str, JobHandler] = {}

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        self._handlers[job_type] = handler

    def submit(self, record: JobRecord, manager: JobManager) -> None:
        self._executor.submit(self._execute, record, manager)

    def _execute(self, record: JobRecord, manager: JobManager) -> None:
        handler = self._handlers.get(record.request.job_type)
        with job_span(
            "job.execute",
            attributes={
                "job.id": record.job_id,
                "job.type": record.request.job_type,
                "job.tenant": record.request.tenant,
            },
        ):
            manager.update_status(record.job_id, JobStatus.RUNNING)
            log_pointer: Optional[str] = None
            try:
                if handler:
                    log_pointer = handler(record, manager)
                manager.update_status(
                    record.job_id,
                    JobStatus.SUCCEEDED,
                    log_pointer=log_pointer,
                )
            except Exception as exc:  # pragma: no cover - handler failure path
                manager.record_failure(record.job_id, str(exc), record)
