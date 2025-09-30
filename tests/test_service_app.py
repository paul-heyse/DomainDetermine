from __future__ import annotations

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "1")
os.environ.setdefault("OTEL_METRICS_EXPORTER", "none")
os.environ.setdefault("OTEL_TRACES_EXPORTER", "none")

import time
from pathlib import Path
from typing import Dict

import pytest
from fastapi.testclient import TestClient

from DomainDetermine.governance.event_log import GovernanceEventLog, GovernanceEventType
from DomainDetermine.service import InMemoryRegistry, JobManager, create_app


def auth_headers(actor: str = "user", roles: str = "admin", tenant: str = "tenant-a") -> Dict[str, str]:
    return {
        "X-Actor": actor,
        "X-Roles": roles,
        "X-Tenant": tenant,
        "X-Reason": "tests",
    }


@pytest.fixture()
def registry() -> InMemoryRegistry:
    registry = InMemoryRegistry()
    registry.set_quota("tenant-a", "plan-build", 2)
    return registry


@pytest.fixture()
def event_log(tmp_path: Path) -> GovernanceEventLog:
    return GovernanceEventLog(tmp_path / "events.jsonl", secret="test-secret")


@pytest.fixture()
def client(registry: InMemoryRegistry, event_log: GovernanceEventLog) -> TestClient:
    app = create_app(JobManager(registry), event_log=event_log)
    test_client = TestClient(app)
    test_client.app = app  # type: ignore[attr-defined]
    test_client.app.state.event_log = event_log  # type: ignore[attr-defined]
    return test_client


def _wait_for_status(client: TestClient, job_id: str, desired: str, timeout: float = 2.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/jobs/{job_id}", headers=auth_headers())
        if resp.status_code == 200 and resp.json()["status"] == desired:
            return
        time.sleep(0.05)
    assert False, f"Job {job_id} did not reach status {desired}"


def test_health_and_ready(client: TestClient) -> None:
    health = client.get("/healthz", headers=auth_headers())
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert any(dep["name"] == "registry" for dep in body["dependencies"])
    assert body["slow_queries"] == []

    ready = client.get("/readyz", headers=auth_headers())
    assert ready.status_code == 200
    ready_body = ready.json()
    assert ready_body["status"] == "ready"
    assert isinstance(ready_body["slow_queries"], list)

    tracker = client.app.state.slow_request_tracker
    tracker.record("/jobs", 1000.0)
    degraded = client.get("/readyz", headers=auth_headers())
    assert degraded.status_code == 200
    degraded_body = degraded.json()
    assert degraded_body["status"] == "not-ready"
    assert degraded_body["slow_queries"]


def test_artifact_crud(client: TestClient, registry: InMemoryRegistry) -> None:
    create_resp = client.post(
        "/artifacts",
        json={
            "name": "report",
            "type": "pdf",
            "metadata": {"version": "1"},
            "content": "hello world",
            "content_type": "text/plain",
        },
        headers=auth_headers(),
    )
    assert create_resp.status_code == 201
    artifact_id = create_resp.json()["artifact_id"]
    assert create_resp.json()["download_available"] is True

    list_resp = client.get("/artifacts", headers=auth_headers(roles="viewer"))
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) == 1

    update_resp = client.put(
        f"/artifacts/{artifact_id}",
        json={"metadata": {"version": "2"}, "content": "updated", "content_type": "text/plain"},
        headers=auth_headers(),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["metadata"]["version"] == "2"

    download_resp = client.get(
        f"/artifacts/{artifact_id}/download",
        headers=auth_headers(roles="viewer"),
    )
    assert download_resp.status_code == 200
    assert download_resp.text == "updated"

    delete_resp = client.delete(f"/artifacts/{artifact_id}", headers=auth_headers())
    assert delete_resp.status_code == 204


def test_jobs_and_quota(client: TestClient, registry: InMemoryRegistry) -> None:
    first = client.post(
        "/jobs",
        json={
            "job_type": "plan-build",
            "tenant": "tenant-a",
            "project": "proj",
            "payload": {"plan": "1"},
        },
        headers=auth_headers(roles="viewer"),
    )
    assert first.status_code == 202
    job_id = first.json()["job_id"]

    _wait_for_status(client, job_id, "succeeded")
    detail = client.get(f"/jobs/{job_id}", headers=auth_headers())
    assert detail.json()["status"] == "succeeded"

    logs = client.get(f"/jobs/{job_id}/logs", headers=auth_headers())
    assert logs.status_code == 200
    assert "plan build completed" in logs.text

    quotas = client.get("/quotas", headers=auth_headers())
    assert quotas.status_code == 200
    assert quotas.json()[0]["used"] == 1

    client.post(
        "/jobs",
        json={
            "job_type": "plan-build",
            "tenant": "tenant-a",
            "project": "proj",
            "payload": {"plan": "2"},
        },
        headers=auth_headers(roles="viewer"),
    )
    third = client.post(
        "/jobs",
        json={
            "job_type": "plan-build",
            "tenant": "tenant-a",
            "project": "proj",
            "payload": {"plan": "3"},
        },
        headers=auth_headers(roles="viewer"),
    )
    assert third.status_code == 429
    assert third.headers.get("Retry-After") is not None
    quota_detail = third.json()
    assert quota_detail["detail"]["quota"]["type"] == "plan-build"

    events = list(client.app.state.event_log.query())  # type: ignore[attr-defined]
    tenant_events = [
        event
        for event in events
        if event.artifact.artifact_id.startswith("service-job:tenant-a")
    ]
    event_types = {event.event_type for event in tenant_events}
    assert GovernanceEventType.SERVICE_JOB_ENQUEUED in event_types
    assert GovernanceEventType.SERVICE_JOB_COMPLETED in event_types
    assert GovernanceEventType.SERVICE_JOB_QUOTA_EXCEEDED in event_types
