from __future__ import annotations

from typing import Dict

import pytest
from fastapi.testclient import TestClient

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
def client(registry: InMemoryRegistry) -> TestClient:
    app = create_app(JobManager(registry))
    return TestClient(app)


def test_health_and_ready(client: TestClient) -> None:
    health = client.get("/healthz", headers=auth_headers())
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = client.get("/readyz", headers=auth_headers())
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_artifact_crud(client: TestClient, registry: InMemoryRegistry) -> None:
    create_resp = client.post(
        "/artifacts",
        json={"name": "report", "type": "pdf", "metadata": {"version": "1"}},
        headers=auth_headers(),
    )
    assert create_resp.status_code == 201
    artifact_id = create_resp.json()["artifact_id"]

    list_resp = client.get("/artifacts", headers=auth_headers(roles="viewer"))
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) == 1

    update_resp = client.put(
        f"/artifacts/{artifact_id}",
        json={"metadata": {"version": "2"}},
        headers=auth_headers(),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["metadata"]["version"] == "2"

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

    detail = client.get(f"/jobs/{job_id}", headers=auth_headers())
    assert detail.status_code == 200

    logs = client.get(f"/jobs/{job_id}/logs", headers=auth_headers())
    assert logs.status_code == 200

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


