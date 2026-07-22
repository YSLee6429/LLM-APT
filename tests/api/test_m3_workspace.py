from fastapi.testclient import TestClient


def login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "llmapt-local-change-me"},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_and_current_user(anonymous_client: TestClient) -> None:
    rejected = anonymous_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert rejected.status_code == 401

    token = login(anonymous_client)
    response = anonymous_client.get("/api/v1/auth/me", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["role"] == "admin"

    assert anonymous_client.get("/api/v1/auth/me").status_code == 401


def test_guest_session_is_temporary_and_can_use_safe_workspace(
    anonymous_client: TestClient,
) -> None:
    created = anonymous_client.post("/api/v1/auth/guest")
    assert created.status_code == 201
    payload = created.json()
    assert payload["user"]["role"] == "guest"
    guest_headers = auth(str(payload["access_token"]))

    project = anonymous_client.post(
        "/api/v1/projects",
        headers=guest_headers,
        json={"name": "Temporary exploration", "description": "Guest-owned workspace"},
    )
    assert project.status_code == 201
    assert (
        anonymous_client.get("/api/v1/projects", headers=guest_headers).json()[0]["project_id"]
        == project.json()["project_id"]
    )
    assert (
        anonymous_client.post(
            "/api/v1/providers/generate",
            headers=guest_headers,
            json={"provider_key": "mock", "prompt": "solve", "language": "python"},
        ).status_code
        == 403
    )


def test_admin_can_change_password(anonymous_client: TestClient) -> None:
    token = login(anonymous_client)
    changed = anonymous_client.post(
        "/api/v1/auth/change-password",
        headers=auth(token),
        json={
            "current_password": "llmapt-local-change-me",
            "new_password": "a-new-local-password",
        },
    )
    assert changed.status_code == 204
    relogin = anonymous_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "a-new-local-password"},
    )
    assert relogin.status_code == 200


def test_login_is_rate_limited(anonymous_client: TestClient) -> None:
    for _ in range(5):
        response = anonymous_client.post(
            "/api/v1/auth/login",
            json={"username": "missing", "password": "wrong"},
        )
        assert response.status_code == 401
    blocked = anonymous_client.post(
        "/api/v1/auth/login",
        json={"username": "missing", "password": "wrong"},
    )
    assert blocked.status_code == 429


def test_project_and_model_profile_lifecycle(client: TestClient) -> None:
    token = login(client)
    created = client.post(
        "/api/v1/projects",
        headers=auth(token),
        json={"name": "Boundary Research", "description": "Local reproducible study"},
    )
    assert created.status_code == 201
    project_id = created.json()["project_id"]

    profile = client.post(
        f"/api/v1/projects/{project_id}/model-profiles",
        headers=auth(token),
        json={
            "name": "Deterministic baseline",
            "provider": "local",
            "model": "deterministic-coder",
            "revision": "m3",
            "description": "Offline acceptance provider",
            "tags": ["offline", "baseline", "offline"],
        },
    )
    assert profile.status_code == 201
    assert profile.json()["tags"] == ["offline", "baseline"]

    listing = client.get("/api/v1/projects", headers=auth(token))
    assert listing.status_code == 200
    assert listing.json()[0]["model_profile_count"] == 1

    profiles = client.get(f"/api/v1/projects/{project_id}/model-profiles", headers=auth(token))
    assert profiles.status_code == 200
    assert profiles.json()[0]["model"] == "deterministic-coder"


def test_dashboard_and_report_boundaries(client: TestClient) -> None:
    token = login(client)
    dashboard = client.get("/api/v1/dashboard", headers=auth(token))
    assert dashboard.status_code == 200
    assert dashboard.json()["evidence_reports"] == 0
    assert dashboard.json()["recent_experiments"] == []

    reports = client.get("/api/v1/reports", headers=auth(token))
    assert reports.status_code == 200
    assert reports.json() == []

    missing = client.get(
        "/api/v1/reports/00000000-0000-0000-0000-000000000001/export?format=markdown",
        headers=auth(token),
    )
    assert missing.status_code == 404
