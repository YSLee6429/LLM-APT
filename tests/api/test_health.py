from fastapi.testclient import TestClient

from llmapt.api import create_app
from llmapt.application.readiness import StaticReadinessProbe
from llmapt.config import Settings


def test_liveness(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "LLM-APT"
    assert response.headers["X-Request-ID"]


def test_request_id_is_preserved(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "test-request-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_readiness_reports_all_dependencies(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    components = response.json()["components"]
    assert components == {
        "configuration": "ready",
        "database": "ready",
        "broker": "ready",
        "redis": "ready",
        "object_store": "ready",
        "runner": "ready",
    }


def test_versioned_metadata(client: TestClient) -> None:
    response = client.get("/api/v1/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "LLM-APT",
        "version": "0.4.0",
        "environment": "test",
    }


def test_readiness_returns_503_for_an_unavailable_dependency(
    test_settings: Settings,
) -> None:
    probe = StaticReadinessProbe(
        {
            "configuration": "ready",
            "database": "unavailable",
            "broker": "ready",
            "redis": "ready",
            "object_store": "ready",
            "runner": "ready",
        }
    )

    with TestClient(create_app(test_settings, readiness_probe=probe)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
