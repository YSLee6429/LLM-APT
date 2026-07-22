import pytest

from llmapt.domain.enums import OutputPolicy
from llmapt.domain.errors import InvalidProblemError
from llmapt.domain.problems import ProblemSpec, ResourceLimits
from llmapt.domain.problems import TestCase as ProblemTestCase


def test_problem_requires_unique_test_case_ids() -> None:
    duplicate = ProblemTestCase("case-1", b"1\n", b"1\n")

    with pytest.raises(InvalidProblemError, match="unique"):
        ProblemSpec(
            problem_id="identity",
            title="Identity",
            statement="Print the input.",
            language="cpp",
            tests=(duplicate, duplicate),
            limits=ResourceLimits(time_limit_ms=1000, memory_limit_mb=128),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("time_limit_ms", 0),
        ("memory_limit_mb", 0),
        ("process_limit", 0),
        ("output_limit_bytes", 0),
    ],
)
def test_resource_limits_must_be_positive(field: str, value: int) -> None:
    values = {
        "time_limit_ms": 1000,
        "memory_limit_mb": 128,
        "process_limit": 1,
        "output_limit_bytes": 1024,
    }
    values[field] = value

    with pytest.raises(InvalidProblemError, match="positive"):
        ResourceLimits(**values)


def test_problem_digests_are_stable_and_sensitive_to_tests() -> None:
    first = ProblemTestCase("case-1", b"1\n", b"2\n")
    second = ProblemTestCase("case-1", b"1\n", b"3\n")
    limits = ResourceLimits(time_limit_ms=1000, memory_limit_mb=128)
    base = ProblemSpec(
        problem_id="increment",
        title="Increment",
        statement="Print n + 1.",
        language="cpp",
        tests=(first,),
        limits=limits,
        output_policy=OutputPolicy.TOKEN,
    )
    changed = ProblemSpec(
        problem_id="increment",
        title="Increment",
        statement="Print n + 1.",
        language="cpp",
        tests=(second,),
        limits=limits,
        output_policy=OutputPolicy.TOKEN,
    )

    assert len(base.statement_digest) == 64
    assert len(base.test_suite_digest) == 64
    assert base.statement_digest == changed.statement_digest
    assert base.test_suite_digest != changed.test_suite_digest
