"""Readiness contracts used by delivery layers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


class ReadinessProbe(Protocol):
    async def check(self) -> Mapping[str, str]: ...


@dataclass(frozen=True, slots=True)
class StaticReadinessProbe:
    """Deterministic probe used by tests and offline composition."""

    components: Mapping[str, str]

    async def check(self) -> Mapping[str, str]:
        return dict(self.components)
