from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from llmapt.api import create_app
from llmapt.application.readiness import StaticReadinessProbe
from llmapt.config import Environment, Settings


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        environment=Environment.TEST,
        log_level="WARNING",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        broker_url="memory://",
        redis_url="redis://localhost:6379/15",
        object_store_endpoint="http://localhost:9000",
        auth_secret="test-auth-secret-do-not-use",
        bootstrap_admin_password="llmapt-local-change-me",
        runner_token="test-runner-token-do-not-use",
        external_model_calls_enabled=False,
        model_api_key=None,
    )


@pytest.fixture
def anonymous_client(test_settings: Settings) -> Iterator[TestClient]:
    probe = StaticReadinessProbe(
        {
            "configuration": "ready",
            "database": "ready",
            "broker": "ready",
            "redis": "ready",
            "object_store": "ready",
            "runner": "ready",
        }
    )
    with TestClient(create_app(test_settings, readiness_probe=probe)) as test_client:
        yield test_client


@pytest.fixture
def client(anonymous_client: TestClient) -> Iterator[TestClient]:
    response = anonymous_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "llmapt-local-change-me"},
    )
    assert response.status_code == 200
    anonymous_client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    yield anonymous_client
