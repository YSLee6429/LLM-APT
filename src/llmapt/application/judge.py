"""Deterministic output comparison and execution classification."""

from __future__ import annotations

from llmapt.application.ports import ExecutionResult
from llmapt.domain.enums import OutputPolicy, Verdict


def _normalize_newlines(payload: bytes) -> bytes:
    return payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _trim_trailing_whitespace(payload: bytes) -> bytes:
    lines = [line.rstrip(b" \t") for line in _normalize_newlines(payload).split(b"\n")]
    while lines and not lines[-1]:
        lines.pop()
    return b"\n".join(lines)


def outputs_match(expected: bytes, actual: bytes, policy: OutputPolicy) -> bool:
    """Compare byte output according to an explicit policy."""

    normalized_expected = _normalize_newlines(expected)
    normalized_actual = _normalize_newlines(actual)
    if policy is OutputPolicy.EXACT:
        return normalized_expected == normalized_actual
    if policy is OutputPolicy.TRIM_TRAILING_WHITESPACE:
        return _trim_trailing_whitespace(expected) == _trim_trailing_whitespace(actual)
    if policy is OutputPolicy.TOKEN:
        return normalized_expected.split() == normalized_actual.split()
    raise AssertionError(f"unsupported output policy: {policy}")


def classify_execution(
    result: ExecutionResult,
    expected_output: bytes,
    policy: OutputPolicy,
) -> Verdict:
    """Map runner facts to a stable verdict without model interpretation."""

    if result.infrastructure_error:
        return Verdict.INFRASTRUCTURE_ERROR
    if result.timed_out:
        return Verdict.TIME_LIMIT_EXCEEDED
    if result.memory_exceeded:
        return Verdict.MEMORY_LIMIT_EXCEEDED
    if result.output_exceeded:
        return Verdict.OUTPUT_LIMIT_EXCEEDED
    if result.exit_code != 0:
        return Verdict.RUNTIME_ERROR
    if outputs_match(expected_output, result.stdout, policy):
        return Verdict.ACCEPTED
    return Verdict.WRONG_ANSWER
