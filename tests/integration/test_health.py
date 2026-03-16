"""Integration tests for health endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_ready_returns_200(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert "ready" in data


def test_projects_stub(client):
    resp = client.get("/projects/")
    assert resp.status_code == 200
    assert "Not yet implemented" in resp.json()["message"]


def test_patients_stub(client):
    resp = client.get("/patients/")
    assert resp.status_code == 200


def test_pipeline_extract_stub(client):
    resp = client.post("/pipeline/extract")
    assert resp.status_code == 200


def test_export_csv_stub(client):
    resp = client.post("/export/csv")
    assert resp.status_code == 200
