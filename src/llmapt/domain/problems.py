"""Immutable programming-problem and test-case definitions."""

from __future__ import annotations

from dataclasses import dataclass

from llmapt.domain.digests import digest_bytes, digest_text
from llmapt.domain.enums import OutputPolicy
from llmapt.domain.errors import InvalidProblemError


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    time_limit_ms: int
    memory_limit_mb: int
    process_limit: int = 1
    output_limit_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        if self.time_limit_ms < 1:
            raise InvalidProblemError("time_limit_ms must be positive")
        if self.memory_limit_mb < 1:
            raise InvalidProblemError("memory_limit_mb must be positive")
        if self.process_limit < 1:
            raise InvalidProblemError("process_limit must be positive")
        if self.output_limit_bytes < 1:
            raise InvalidProblemError("output_limit_bytes must be positive")


@dataclass(frozen=True, slots=True)
class TestCase:
    case_id: str
    standard_input: bytes
    expected_output: bytes
    hidden: bool = True

    def __post_init__(self) -> None:
        if not self.case_id or self.case_id.strip() != self.case_id:
            raise InvalidProblemError("case_id must be non-empty and trimmed")
        if len(self.case_id) > 128:
            raise InvalidProblemError("case_id must not exceed 128 characters")

    @property
    def input_digest(self) -> str:
        return digest_bytes(self.standard_input)

    @property
    def expected_output_digest(self) -> str:
        return digest_bytes(self.expected_output)


@dataclass(frozen=True, slots=True)
class ProblemSpec:
    problem_id: str
    title: str
    statement: str
    language: str
    tests: tuple[TestCase, ...]
    limits: ResourceLimits
    output_policy: OutputPolicy = OutputPolicy.TRIM_TRAILING_WHITESPACE

    def __post_init__(self) -> None:
        if not self.problem_id or self.problem_id.strip() != self.problem_id:
            raise InvalidProblemError("problem_id must be non-empty and trimmed")
        if not self.title.strip():
            raise InvalidProblemError("title must be non-empty")
        if not self.statement.strip():
            raise InvalidProblemError("statement must be non-empty")
        if not self.language.strip():
            raise InvalidProblemError("language must be non-empty")
        if not self.tests:
            raise InvalidProblemError("a problem must contain at least one test case")
        case_ids = [case.case_id for case in self.tests]
        if len(case_ids) != len(set(case_ids)):
            raise InvalidProblemError("test case identifiers must be unique")

    @property
    def statement_digest(self) -> str:
        return digest_text(self.statement)

    @property
    def test_suite_digest(self) -> str:
        material = "\n".join(
            f"{case.case_id}:{case.input_digest}:{case.expected_output_digest}"
            for case in self.tests
        )
        return digest_text(material)
