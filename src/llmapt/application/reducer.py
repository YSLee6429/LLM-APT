"""Deterministic token delta debugging for legal failing inputs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

FailurePredicate = Callable[[bytes], Awaitable[bool]]


@dataclass(frozen=True, slots=True)
class ReductionResult:
    minimized_input: bytes
    attempts: int


class TokenDeltaReducer:
    def __init__(self, max_attempts: int = 64) -> None:
        self._max_attempts = max_attempts

    async def reduce(self, original: bytes, predicate: FailurePredicate) -> ReductionResult:
        tokens = original.split()
        attempts = 0
        if not tokens:
            return ReductionResult(original, attempts)

        normalized = b" ".join(tokens)
        attempts += 1
        if await predicate(normalized):
            current = tokens
        else:
            current = tokens
            normalized = original

        granularity = 2
        while len(current) >= 2 and attempts < self._max_attempts:
            chunk_size = max(1, (len(current) + granularity - 1) // granularity)
            reduced = False
            for start in range(0, len(current), chunk_size):
                candidate_tokens = current[:start] + current[start + chunk_size :]
                if not candidate_tokens:
                    continue
                candidate = b" ".join(candidate_tokens)
                attempts += 1
                if await predicate(candidate):
                    current = candidate_tokens
                    normalized = candidate
                    granularity = max(2, granularity - 1)
                    reduced = True
                    break
                if attempts >= self._max_attempts:
                    break
            if reduced:
                continue
            if granularity >= len(current):
                break
            granularity = min(len(current), granularity * 2)
        return ReductionResult(normalized, attempts)
