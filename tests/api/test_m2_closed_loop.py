from fastapi.testclient import TestClient

from llmapt.api import create_app
from llmapt.application.ports import ExecutionResult
from llmapt.config import Settings
from llmapt.infrastructure.memory import ScriptedSandbox


def _authenticate(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "llmapt-local-change-me"},
    )
    assert response.status_code == 200
    token = str(response.json()["access_token"])
    client.headers["Authorization"] = f"Bearer {token}"
    return token


def _problem() -> dict[str, object]:
    return {
        "problem_id": "double",
        "title": "Double",
        "statement": "Read one integer n and print 2 * n.",
        "language": "cpp",
        "tests": [
            {"case_id": "positive", "standard_input": "2\n", "expected_output": "4\n"},
            {"case_id": "negative", "standard_input": "-3\n", "expected_output": "-6\n"},
        ],
        "limits": {"time_limit_ms": 1000, "memory_limit_mb": 128},
    }


def test_complete_review_execution_reproduction_and_report_api(test_settings: Settings) -> None:
    sandbox = ScriptedSandbox(
        executions={
            b"-3\n": ExecutionResult(0, b"0\n", b"", 1),
            b"-3": ExecutionResult(0, b"0\n", b"", 1),
        }
    )
    with TestClient(create_app(test_settings, sandbox=sandbox)) as client:
        token = _authenticate(client)
        proposal = client.post(
            "/api/v1/mutations/propose",
            json={
                "problem": _problem(),
                "operator": "test_order_rotation",
                "random_seed": 1,
            },
        ).json()
        candidate_id = proposal["candidate_id"]
        validation = client.post(
            "/api/v1/oracles/validate",
            json={"candidate_id": candidate_id, "oracle_key": "builtin.double"},
        )
        assert validation.status_code == 200

        del client.headers["Authorization"]
        unauthorized = client.post(
            f"/api/v1/mutations/{candidate_id}/review",
            json={"decision": "approve", "reviewer": "r", "justification": "checked"},
        )
        assert unauthorized.status_code == 401
        client.headers["Authorization"] = f"Bearer {token}"

        review = client.post(
            f"/api/v1/mutations/{candidate_id}/review",
            json={
                "decision": "approve",
                "reviewer": "reviewer@example.test",
                "justification": "Oracle and statement semantics checked.",
            },
        )
        assert review.status_code == 200
        assert review.json()["candidate_status"] == "ready"

        run = client.post(
            "/api/v1/closed-loop/run",
            json={
                "candidate_id": candidate_id,
                "oracle_key": "builtin.double",
                "provider_key": "local",
                "prompt": "Solve and return only C++ source.",
                "repetitions": 2,
                "parameters": {"temperature": 0},
            },
        )
        assert run.status_code == 200
        payload = run.json()
        assert payload["verdict"] == "wrong_answer"
        assert payload["evidence_level"] == 2
        assert payload["stable_failure"] is True
        assert payload["counterexample"]["minimized_size"] == 2

        stored = client.get(f"/api/v1/closed-loop/{payload['report_id']}")
        assert stored.status_code == 200
        assert stored.json() == payload
        assert (
            client.get("/api/v1/closed-loop/00000000-0000-0000-0000-000000000000").status_code
            == 404
        )


def test_closed_loop_rejects_candidate_before_human_review(test_settings: Settings) -> None:
    with TestClient(create_app(test_settings, sandbox=ScriptedSandbox(executions={}))) as client:
        _authenticate(client)
        proposal = client.post(
            "/api/v1/mutations/propose",
            json={"problem": _problem(), "operator": "test_order_rotation"},
        ).json()
        response = client.post(
            "/api/v1/closed-loop/run",
            json={
                "candidate_id": proposal["candidate_id"],
                "oracle_key": "builtin.double",
                "provider_key": "local",
                "prompt": "Solve.",
                "repetitions": 2,
            },
        )

        assert response.status_code == 409
