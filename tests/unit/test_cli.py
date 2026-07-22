import json

import pytest

from llmapt.cli import main


def test_version_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "0.4.0"


def test_doctor_does_not_print_connection_credentials(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["doctor"]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert report["status"] == "ok"
    assert report["database_driver"] == "postgresql+asyncpg"
    assert "local-postgres-change-me" not in captured.out
    assert report["external_model_calls_enabled"] is False


def test_providers_command_lists_local_provider(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["providers"]) == 0
    providers = json.loads(capsys.readouterr().out)

    assert providers == [
        {
            "external": False,
            "key": "local",
            "model": "deterministic-coder",
            "provider": "local",
            "revision": "m2",
        }
    ]


def test_mock_evaluate_command_prints_evidence_report(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["mock-evaluate", "--scenario", "wrong_answer"]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["problem_id"] == "m1-double"
    assert report["verdict"] == "wrong_answer"
    assert report["cases"][1]["verdict"] == "wrong_answer"
