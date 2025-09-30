from __future__ import annotations

from fastapi.testclient import TestClient

from DomainDetermine.gui.app import create_app


def test_root_page_loads() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "DomainDetermine GUI Prototype" in response.text

