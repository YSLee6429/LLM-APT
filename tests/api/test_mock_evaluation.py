from fastapi.testclient import TestClient


def test_mock_evaluation_returns_accepted_report(client: TestClient) -> None:
    response = client.post(
        "/api/v1/evaluations/mock",
        json={"scenario": "accepted", "random_seed": 17},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["problem_id"] == "m1-double"
    assert payload["verdict"] == "accepted"
    assert payload["passed_cases"] == payload["total_cases"] == 2
    assert payload["ephemeral_artifacts"] is True


def test_mock_evaluation_exposes_wrong_answer_case(client: TestClient) -> None:
    response = client.post("/api/v1/evaluations/mock", json={"scenario": "wrong_answer"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] == "wrong_answer"
    assert payload["evidence_level"] == 1
    assert payload["cases"][1]["verdict"] == "wrong_answer"
    assert (
        payload["cases"][1]["expected_output_digest"] != payload["cases"][1]["actual_output_digest"]
    )


def test_mock_compile_error_has_no_executed_cases(client: TestClient) -> None:
    response = client.post("/api/v1/evaluations/mock", json={"scenario": "compile_error"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] == "compile_error"
    assert payload["total_cases"] == 0


def test_mock_evaluation_rejects_unknown_scenario(client: TestClient) -> None:
    response = client.post("/api/v1/evaluations/mock", json={"scenario": "invented"})

    assert response.status_code == 422
