"""Pydantic schemas for the service layer."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    """Represents the health of a downstream dependency."""

    name: str
    status: str
    latency_ms: Optional[float] = None
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    dependencies: List[DependencyStatus]
    slow_queries: List[str] = Field(default_factory=list)


class ReadinessResponse(BaseModel):
    status: str
    pending_migrations: bool
    queue_depth: int


class ArtifactCreateRequest(BaseModel):
    name: str
    type: str
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)


class ArtifactUpdateRequest(BaseModel):
    metadata: Dict[str, str]


class ArtifactResponse(BaseModel):
    artifact_id: str
    name: Optional[str] = None
    type: Optional[str] = None
    metadata: Dict[str, str]
    created_at: datetime
    updated_at: datetime


class ArtifactListResponse(BaseModel):
    items: List[ArtifactResponse]


class JobRequestPayload(BaseModel):
    job_type: str
    tenant: str
    project: str
    payload: Dict[str, str]


class JobResponse(BaseModel):
    job_id: str
    status: str
    retries: int
    submitted_at: datetime
    updated_at: datetime
    log_pointer: Optional[str] = None


class JobListResponse(BaseModel):
    items: List[JobResponse]


class QuotaResponse(BaseModel):
    tenant: str
    quota_type: str
    limit: int
    used: int
    reset_at: datetime

