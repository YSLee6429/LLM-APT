"""Provider discovery without coupling application services to concrete SDKs."""

from __future__ import annotations

from dataclasses import dataclass, field

from llmapt.application.ports import ModelProvider, ModelRequest, ModelResponse
from llmapt.domain.entities import ModelIdentity
from llmapt.domain.errors import EvaluationError


class ProviderNotFoundError(EvaluationError):
    """Raised when a requested provider key is not registered."""


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    key: str
    identity: ModelIdentity
    external: bool


@dataclass(slots=True)
class ProviderRegistry:
    """Explicit registry prevents arbitrary provider selection from request data."""

    _providers: dict[str, ModelProvider] = field(default_factory=dict)
    _external: dict[str, bool] = field(default_factory=dict)

    def register(self, key: str, provider: ModelProvider, *, external: bool) -> None:
        normalized = key.strip().casefold()
        if not normalized:
            raise ValueError("provider key must not be blank")
        if normalized in self._providers:
            raise ValueError(f"provider key already registered: {normalized}")
        self._providers[normalized] = provider
        self._external[normalized] = external

    def get(self, key: str) -> ModelProvider:
        normalized = key.strip().casefold()
        try:
            return self._providers[normalized]
        except KeyError as exc:
            raise ProviderNotFoundError(f"provider is not available: {normalized}") from exc

    async def describe(self) -> tuple[ProviderDescriptor, ...]:
        descriptions: list[ProviderDescriptor] = []
        for key in sorted(self._providers):
            descriptions.append(
                ProviderDescriptor(
                    key=key,
                    identity=await self._providers[key].identify(),
                    external=self._external[key],
                )
            )
        return tuple(descriptions)

    async def generate(self, key: str, request: ModelRequest) -> ModelResponse:
        return await self.get(key).generate(request)
