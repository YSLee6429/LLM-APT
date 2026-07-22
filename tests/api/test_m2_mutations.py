from fastapi.testclient import TestClient


def _problem() -> dict[str, object]:
    return {
        "problem_id": "runs",
        "title": "Runs",
        "statement": "Count equal runs.",
        "language": "cpp",
        "tests": [
            {"case_id": "one", "standard_input": "1\n", "expected_output": "1\n"},
            {"case_id": "last", "standard_input": "3\n1 1 1\n", "expected_output": "1\n"},
        ],
        "limits": {"time_limit_ms": 1000, "memory_limit_mb": 128},
    }


def test_mutation_preview_never_marks_candidate_oracle_valid(client: TestClient) -> None:
    response = client.post(
        "/api/v1/mutations/preview",
        json={
            "problem": _problem(),
            "operator": "boundary_clause",
            "random_seed": 9,
            "boundary_clause": "The final run must be counted.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_oracle_validation"] is True
    assert payload["problem"]["problem_id"] == "runs--boundary-9"
    assert "final run" in payload["problem"]["statement"]
    assert payload["parent_statement_digest"] != payload["problem"]["statement"]


def test_mutation_preview_rejects_missing_clause(client: TestClient) -> None:
    response = client.post(
        "/api/v1/mutations/preview",
        json={"problem": _problem(), "operator": "boundary_clause"},
    )

    assert response.status_code == 422
    assert "non-blank clause" in response.json()["detail"]


def test_persisted_mutation_routes_report_missing_and_invalid_candidates(
    client: TestClient,
) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/v1/mutations/{missing}").status_code == 404
    assert client.get(f"/api/v1/mutations/{missing}/state").status_code == 404

    invalid = client.post(
        "/api/v1/mutations/propose",
        json={"problem": _problem(), "operator": "boundary_clause"},
    )
    assert invalid.status_code == 422
