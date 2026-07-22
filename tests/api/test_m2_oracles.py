from fastapi.testclient import TestClient


def _problem(*, expected_positive: str = "4\n") -> dict[str, object]:
    return {
        "problem_id": "double",
        "title": "Double an Integer",
        "statement": "Read one integer n and print 2 * n.",
        "language": "cpp",
        "tests": [
            {
                "case_id": "positive",
                "standard_input": "2\n",
                "expected_output": expected_positive,
            },
            {
                "case_id": "negative",
                "standard_input": "-3\n",
                "expected_output": "-6\n",
            },
        ],
        "limits": {"time_limit_ms": 1000, "memory_limit_mb": 128},
    }


def _propose(client: TestClient, problem: dict[str, object]) -> dict[str, object]:
    response = client.post(
        "/api/v1/mutations/propose",
        json={
            "problem": problem,
            "operator": "test_order_rotation",
            "random_seed": 17,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_catalog_and_oracle_admission_flow(client: TestClient) -> None:
    catalog = client.get("/api/v1/oracles")
    assert catalog.status_code == 200
    assert catalog.json()[0]["key"] == "builtin.double"

    candidate = _propose(client, _problem())
    candidate_id = candidate["candidate_id"]
    stored = client.get(f"/api/v1/mutations/{candidate_id}")
    initial = client.get(f"/api/v1/mutations/{candidate_id}/state")
    validation = client.post(
        "/api/v1/oracles/validate",
        json={"candidate_id": candidate_id, "oracle_key": "builtin.double"},
    )
    final = client.get(f"/api/v1/mutations/{candidate_id}/state")

    assert stored.status_code == 200
    assert initial.json()["status"] == "generated"
    assert validation.status_code == 200
    assert validation.json()["verdict"] == "passed"
    assert validation.json()["passed_cases"] == 2
    assert final.json()["status"] == "oracle_validated"
    assert final.json()["oracle_validation_id"] == validation.json()["validation_id"]


def test_oracle_rejects_tampered_expected_output(client: TestClient) -> None:
    candidate = _propose(client, _problem(expected_positive="5\n"))
    validation = client.post(
        "/api/v1/oracles/validate",
        json={"candidate_id": candidate["candidate_id"], "oracle_key": "builtin.double"},
    )

    assert validation.status_code == 200
    assert validation.json()["verdict"] == "rejected"
    assert validation.json()["reason_code"] == "oracle_output_mismatch"


def test_oracle_validation_rejects_unknown_identifiers(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    response = client.post(
        "/api/v1/oracles/validate",
        json={"candidate_id": missing, "oracle_key": "builtin.double"},
    )

    assert response.status_code == 404


def test_oracle_validation_rejects_unknown_oracle(client: TestClient) -> None:
    candidate = _propose(client, _problem())
    response = client.post(
        "/api/v1/oracles/validate",
        json={"candidate_id": candidate["candidate_id"], "oracle_key": "unregistered"},
    )

    assert response.status_code == 404
