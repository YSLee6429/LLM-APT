import pytest

from llmapt.application.judge import classify_execution, outputs_match
from llmapt.application.ports import ExecutionResult
from llmapt.domain.enums import OutputPolicy, Verdict


def test_output_policies_are_explicit() -> None:
    expected = b"1  2\r\n"
    actual = b"1 2\n"

    assert not outputs_match(expected, actual, OutputPolicy.EXACT)
    assert not outputs_match(expected, actual, OutputPolicy.TRIM_TRAILING_WHITESPACE)
    assert outputs_match(expected, actual, OutputPolicy.TOKEN)
    assert outputs_match(b"answer  \n\n", b"answer\n", OutputPolicy.TRIM_TRAILING_WHITESPACE)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"infrastructure_error": True}, Verdict.INFRASTRUCTURE_ERROR),
        ({"timed_out": True}, Verdict.TIME_LIMIT_EXCEEDED),
        ({"memory_exceeded": True}, Verdict.MEMORY_LIMIT_EXCEEDED),
        ({"output_exceeded": True}, Verdict.OUTPUT_LIMIT_EXCEEDED),
        ({"exit_code": 7}, Verdict.RUNTIME_ERROR),
        ({"stdout": b"wrong\n"}, Verdict.WRONG_ANSWER),
        ({}, Verdict.ACCEPTED),
    ],
)
def test_execution_facts_map_to_verdicts(
    overrides: dict[str, object],
    expected: Verdict,
) -> None:
    values: dict[str, object] = {
        "exit_code": 0,
        "stdout": b"42\n",
        "stderr": b"",
        "duration_ms": 2,
    }
    values.update(overrides)
    result = ExecutionResult(**values)

    assert classify_execution(result, b"42\n", OutputPolicy.EXACT) is expected
