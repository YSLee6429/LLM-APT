import json
from pathlib import Path

from fastapi.testclient import TestClient


def _example_problem() -> dict[str, object]:
    path = Path(__file__).parents[2] / "examples" / "problems" / "double.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_example_problem_is_valid_and_digestible(client: TestClient) -> None:
    response = client.post("/api/v1/problems/validate", json=_example_problem())

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["problem_id"] == "double"
    assert payload["test_count"] == 2
    assert len(payload["statement_digest"]) == 64
    assert len(payload["test_suite_digest"]) == 64


def test_duplicate_test_case_ids_are_rejected(client: TestClient) -> None:
    definition = _example_problem()
    tests = definition["tests"]
    assert isinstance(tests, list)
    second = tests[1]
    assert isinstance(second, dict)
    second["case_id"] = "sample-positive"

    response = client.post("/api/v1/problems/validate", json=definition)

    assert response.status_code == 422
    assert "unique" in response.json()["detail"]


def test_non_positive_resource_limit_is_rejected(client: TestClient) -> None:
    definition = _example_problem()
    limits = definition["limits"]
    assert isinstance(limits, dict)
    limits["time_limit_ms"] = 0

    response = client.post("/api/v1/problems/validate", json=definition)

    assert response.status_code == 422
