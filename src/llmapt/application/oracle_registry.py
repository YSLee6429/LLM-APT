"""Explicit registry for trusted, server-controlled output oracles."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from llmapt.domain.errors import EvaluationError
from llmapt.domain.oracles import OracleIdentity

OracleEvaluator = Callable[[bytes], bytes]


@dataclass(frozen=True, slots=True)
class RegisteredOracle:
    identity: OracleIdentity
    evaluate: OracleEvaluator


class OracleRegistry:
    def __init__(self, oracles: Iterable[RegisteredOracle] = ()) -> None:
        self._oracles: dict[str, RegisteredOracle] = {}
        for oracle in oracles:
            if oracle.identity.key in self._oracles:
                raise ValueError(f"duplicate oracle key: {oracle.identity.key}")
            self._oracles[oracle.identity.key] = oracle

    def resolve(self, key: str) -> RegisteredOracle:
        try:
            return self._oracles[key]
        except KeyError as exc:
            raise EvaluationError("trusted oracle not found") from exc

    def catalog(self) -> tuple[OracleIdentity, ...]:
        return tuple(self._oracles[key].identity for key in sorted(self._oracles))
