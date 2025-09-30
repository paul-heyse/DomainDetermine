"""FastAPI application setup for the DomainDetermine service layer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from DomainDetermine.governance.event_log import GovernanceEventLog, GovernanceEventType

from .auth import AuthContext, get_auth_context, require_roles
from .events import alert_quota_violation, emit_job_event
from .handlers import register_default_handlers
from .jobs import JobManager, JobRecord, JobRequest, QuotaExceededError, ThreadedJobRunner
from .schemas import (
    ArtifactCreateRequest,
    ArtifactListResponse,
    ArtifactResponse,
    ArtifactUpdateRequest,
    DependencyStatus,
    HealthResponse,
    JobListResponse,
    JobRequestPayload,
    JobResponse,
    QuotaResponse,
    ReadinessResponse,
)
from .telemetry import SlowRequestTracker, TelemetryMiddleware, job_span

ADMIN_ROLES = {"admin", "publisher"}
VIEWER_ROLES = {"viewer", "admin", "publisher"}


def _artifact_to_response(entry) -> ArtifactResponse:
    return ArtifactResponse(
        artifact_id=entry.artifact_id,
        name=entry.name,
        type=entry.type,
        metadata=entry.metadata,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        download_available=bool(getattr(entry, "content", None)),
    )


def _job_to_response(record: JobRecord) -> JobResponse:
    return JobResponse(
        job_id=record.job_id,
        status=record.status.value,
        retries=record.retries,
        submitted_at=record.submitted_at,
        updated_at=record.updated_at,
        log_pointer=record.log_pointer,
    )


def create_app(
    job_manager: JobManager,
    *,
    slow_request_threshold_ms: float = 500.0,
    event_log: GovernanceEventLog | None = None,
) -> FastAPI:
    app = FastAPI(title="DomainDetermine Service", version="0.1.0")
    if job_manager.runner is None:
        job_manager.runner = ThreadedJobRunner()
    if event_log is not None:
        job_manager.event_log = event_log
    slow_tracker = SlowRequestTracker()
    app.state.slow_request_tracker = slow_tracker
    app.add_middleware(
        TelemetryMiddleware,
        slow_query_threshold_ms=slow_request_threshold_ms,
        on_slow_request=slow_tracker.record,
    )
    register_default_handlers(job_manager)
    @app.get("/healthz", response_model=HealthResponse)
    def health(_: AuthContext = Depends(get_auth_context)) -> HealthResponse:
        dependency_statuses: list[DependencyStatus] = []
        overall_status = "ok"
        try:
            list(job_manager.registry.list_artifacts())
            dependency_statuses.append(DependencyStatus(name="registry", status="ok"))
        except Exception as exc:  # pragma: no cover - defensive path
            overall_status = "degraded"
            dependency_statuses.append(DependencyStatus(name="registry", status="error", details=str(exc)))
        runner_status = "ok" if job_manager.runner is not None else "idle"
        dependency_statuses.append(DependencyStatus(name="job_runner", status=runner_status))
        return HealthResponse(
            status=overall_status,
            dependencies=dependency_statuses,
            slow_queries=slow_tracker.snapshot(),
        )

    @app.get("/readyz", response_model=ReadinessResponse)
    def ready(_: AuthContext = Depends(get_auth_context)) -> ReadinessResponse:
        try:
            queue_depth = len(list(job_manager.list()))
            registry_ok = True
        except Exception:  # pragma: no cover - defensive path
            queue_depth = -1
            registry_ok = False
        runner_ready = job_manager.runner is not None
        slow_queries = slow_tracker.snapshot()
        status_text = "ready" if registry_ok and runner_ready and not slow_queries else "not-ready"
        response = ReadinessResponse(
            status=status_text,
            pending_migrations=False,
            queue_depth=queue_depth,
            slow_queries=slow_queries,
        )
        return response

    @app.post(
        "/artifacts",
        response_model=ArtifactResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_artifact(
        payload: ArtifactCreateRequest,
        auth: AuthContext = Depends(get_auth_context),
    ) -> ArtifactResponse:
        require_roles(auth, ADMIN_ROLES)
        artifact_id = job_manager.registry.create_artifact(payload)
        entry = job_manager.registry.get_artifact(artifact_id)
        return _artifact_to_response(entry)

    @app.get("/artifacts", response_model=ArtifactListResponse)
    def list_artifacts(auth: AuthContext = Depends(get_auth_context)) -> ArtifactListResponse:
        require_roles(auth, VIEWER_ROLES)
        entries = job_manager.registry.list_artifacts()
        return ArtifactListResponse(items=[_artifact_to_response(e) for e in entries])

    @app.put("/artifacts/{artifact_id}", response_model=ArtifactResponse)
    def update_artifact(
        artifact_id: str,
        payload: ArtifactUpdateRequest,
        auth: AuthContext = Depends(get_auth_context),
    ) -> ArtifactResponse:
        require_roles(auth, ADMIN_ROLES)
        job_manager.registry.update_artifact(
            artifact_id,
            payload.metadata,
            content=payload.content,
            content_type=payload.content_type,
        )
        entry = job_manager.registry.artifacts[artifact_id]
        return _artifact_to_response(entry)

    @app.get("/artifacts/{artifact_id}/download")
    def download_artifact(
        artifact_id: str,
        auth: AuthContext = Depends(get_auth_context),
    ):
        require_roles(auth, VIEWER_ROLES)
        content, content_type = job_manager.registry.get_artifact_payload(artifact_id)
        if not content:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact content not available")
        return StreamingResponse(iter([content]), media_type=content_type)

    @app.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_artifact(
        artifact_id: str,
        auth: AuthContext = Depends(get_auth_context),
    ) -> Response:
        require_roles(auth, ADMIN_ROLES)
        job_manager.registry.delete_artifact(artifact_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
    def submit_job(
        payload: JobRequestPayload,
        auth: AuthContext = Depends(get_auth_context),
    ) -> JobResponse:
        require_roles(auth, VIEWER_ROLES)
        request = JobRequest(
            job_type=payload.job_type,
            payload=payload.payload,
            tenant=payload.tenant,
            project=payload.project,
            actor=auth.actor,
            reason=auth.reason,
        )
        try:
            with job_span(
                "job.enqueue",
                attributes={
                    "job.type": payload.job_type,
                    "job.tenant": payload.tenant,
                    "job.project": payload.project,
                },
            ):
                record = job_manager.enqueue(request)
        except QuotaExceededError as exc:  # pragma: no cover - simple error mapping
            detail = {
                "message": str(exc),
                "quota": {
                    "type": exc.quota_type,
                    "limit": exc.limit,
                    "used": exc.used,
                },
            }
            job_manager_event_log = job_manager.event_log
            emit_job_event(
                event_log=job_manager_event_log,
                event_type=GovernanceEventType.SERVICE_JOB_QUOTA_EXCEEDED,
                job_id=f"pending:{payload.job_type}",
                tenant=payload.tenant,
                actor=auth.actor,
                payload={
                    "job_type": payload.job_type,
                    "project": payload.project,
                    "quota_type": exc.quota_type,
                    "limit": exc.limit,
                    "used": exc.used,
                },
            )
            alert_quota_violation(
                job_id=f"pending:{payload.job_type}",
                tenant=payload.tenant,
                quota_type=exc.quota_type,
                used=exc.used,
                limit=exc.limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
                headers={"Retry-After": str(exc.retry_after_seconds)},
            ) from exc
        return _job_to_response(record)

    @app.get("/jobs", response_model=JobListResponse)
    def list_jobs(
        tenant: Optional[str] = None,
        auth: AuthContext = Depends(get_auth_context),
    ) -> JobListResponse:
        require_roles(auth, VIEWER_ROLES)
        records = job_manager.list(tenant=tenant or auth.tenant)
        return JobListResponse(items=[_job_to_response(r) for r in records])

    @app.get("/jobs/{job_id}", response_model=JobResponse)
    def get_job(job_id: str, auth: AuthContext = Depends(get_auth_context)) -> JobResponse:
        require_roles(auth, VIEWER_ROLES)
        record = job_manager.get(job_id)
        return _job_to_response(record)

    @app.get("/jobs/{job_id}/logs")
    def stream_job_logs(job_id: str, auth: AuthContext = Depends(get_auth_context)):
        require_roles(auth, VIEWER_ROLES)
        return StreamingResponse(job_manager.stream_logs(job_id), media_type="text/plain")

    @app.get("/quotas", response_model=list[QuotaResponse])
    def quotas(auth: AuthContext = Depends(get_auth_context)) -> list[QuotaResponse]:
        require_roles(auth, VIEWER_ROLES)
        usage = job_manager.registry.quota_usage(auth.tenant)
        limits = job_manager.registry.quota_limits(auth.tenant)
        now = datetime.now(timezone.utc)
        responses: list[QuotaResponse] = []
        for quota_type, limit in limits.items():
            responses.append(
                QuotaResponse(
                    tenant=auth.tenant,
                    quota_type=quota_type,
                    limit=limit,
                    used=usage.get(quota_type, 0),
                    reset_at=now + timedelta(days=1),
                )
            )
        return responses

    return app
