from fastapi.testclient import TestClient


def _problem() -> dict[str, object]:
    return {
        "problem_id": "double",
        "title": "Double",
        "statement": "Print twice the input.",
        "language": "cpp",
        "tests": [{"case_id": "one", "standard_input": "1\n", "expected_output": "2\n"}],
        "limits": {"time_limit_ms": 1000, "memory_limit_mb": 128},
    }


def test_provider_catalog_exposes_safe_local_provider(client: TestClient) -> None:
    response = client.get("/api/v1/providers")

    assert response.status_code == 200
    assert response.json() == [
        {
            "key": "local",
            "identity": {
                "provider": "local",
                "model": "deterministic-coder",
                "revision": "m2",
            },
            "external": False,
        }
    ]


def test_local_generation_returns_source_and_digests(client: TestClient) -> None:
    response = client.post(
        "/api/v1/providers/generate",
        json={"provider_key": "local", "prompt": "Solve it", "language": "cpp"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["identity"]["provider"] == "local"
    assert "int main" in payload["source"]
    assert len(payload["source_digest"]) == 64
    assert payload["extracted_from_fence"] is False


def test_generation_rejects_unregistered_provider(client: TestClient) -> None:
    response = client.post(
        "/api/v1/providers/generate",
        json={"provider_key": "invented", "prompt": "Solve it", "language": "cpp"},
    )

    assert response.status_code == 404


def test_experiment_plan_is_canonical_and_reproducible(client: TestClient) -> None:
    request = {
        "problem": _problem(),
        "provider_key": "local",
        "prompt_template_version": "m2-v1",
        "random_seed": 17,
        "repetitions": 2,
        "parameters": {"temperature": 0, "max_tokens": 1024},
    }

    first = client.post("/api/v1/experiments/plan", json=request)
    second = client.post("/api/v1/experiments/plan", json=request)

    assert first.status_code == second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["experiment_id"] != second_payload["experiment_id"]
    assert first_payload["plan_digest"] == second_payload["plan_digest"]
    assert first_payload["parameters"] == {"max_tokens": 1024, "temperature": 0}
    assert first_payload["target"]["revision"] == "m2"
    stored = client.get(f"/api/v1/experiments/{first_payload['experiment_id']}")
    assert stored.status_code == 200
    assert stored.json()["plan_digest"] == first_payload["plan_digest"]
    assert stored.json()["ephemeral_storage"] is True
    state = client.get(f"/api/v1/experiments/{first_payload['experiment_id']}/state")
    assert state.status_code == 200
    assert state.json()["status"] == "planned"

    queued = client.post(f"/api/v1/experiments/{first_payload['experiment_id']}/enqueue")
    assert queued.status_code == 200
    assert queued.json()["status"] == "queued"
    assert queued.json()["task_id"]

    duplicate = client.post(f"/api/v1/experiments/{first_payload['experiment_id']}/enqueue")
    assert duplicate.status_code == 409


def test_missing_experiment_returns_not_found(client: TestClient) -> None:
    missing_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/experiments/{missing_id}")

    assert response.status_code == 404
    assert client.get(f"/api/v1/experiments/{missing_id}/state").status_code == 404
    assert client.post(f"/api/v1/experiments/{missing_id}/enqueue").status_code == 404
