"""FastAPI application setup for the DomainDetermine service layer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from .auth import AuthContext, get_auth_context, require_roles
from .jobs import JobManager, JobRecord, JobRequest, QuotaExceededError
from .schemas import (
    ArtifactCreateRequest,
    ArtifactListResponse,
    ArtifactResponse,
    ArtifactUpdateRequest,
    HealthResponse,
    JobListResponse,
    JobRequestPayload,
    JobResponse,
    QuotaResponse,
    ReadinessResponse,
)

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


def create_app(job_manager: JobManager) -> FastAPI:
    app = FastAPI(title="DomainDetermine Service", version="0.1.0")
    @app.get("/healthz", response_model=HealthResponse)
    def health(_: AuthContext = Depends(get_auth_context)) -> HealthResponse:
        # In a real deployment dependency statuses would be collected here.
        return HealthResponse(status="ok", dependencies=[], slow_queries=[])

    @app.get("/readyz", response_model=ReadinessResponse)
    def ready(_: AuthContext = Depends(get_auth_context)) -> ReadinessResponse:
        return ReadinessResponse(status="ready", pending_migrations=False, queue_depth=0)

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
        job_manager.registry.update_artifact(artifact_id, payload.metadata)
        entry = job_manager.registry.artifacts[artifact_id]
        return _artifact_to_response(entry)

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
            record = job_manager.enqueue(request)
        except QuotaExceededError as exc:  # pragma: no cover - simple error mapping
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
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

