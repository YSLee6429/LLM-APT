"""Construct the explicit process-level provider registry from validated settings."""

from llmapt.application.provider_registry import ProviderRegistry
from llmapt.config import Environment, Settings
from llmapt.domain.entities import ModelIdentity
from llmapt.infrastructure.memory import DeterministicModelProvider
from llmapt.infrastructure.providers.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)

_LOCAL_SOURCE = """#include <iostream>
int main() {
    std::cout << 0 << '\\n';
    return 0;
}
"""


def build_provider_registry(settings: Settings) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(
        "local",
        DeterministicModelProvider(
            source=_LOCAL_SOURCE,
            identity=ModelIdentity(
                provider="local",
                model="deterministic-coder",
                revision="m2",
            ),
        ),
        external=False,
    )

    if settings.external_model_calls_enabled:
        missing = [
            name
            for name, value in (
                ("model_name", settings.model_name),
                ("model_api_endpoint", settings.model_api_endpoint),
                ("model_api_key", settings.model_api_key),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "external model calls are enabled but settings are missing: " + ", ".join(missing)
            )
        if (
            settings.environment is Environment.PRODUCTION
            and not settings.model_api_endpoint.startswith("https://")
        ):
            raise ValueError("production model_api_endpoint must use HTTPS")
        if settings.model_api_key is None:  # guarded by the missing-settings check
            raise AssertionError("model_api_key validation invariant failed")
        registry.register(
            settings.model_provider_key,
            OpenAICompatibleProvider(
                OpenAICompatibleConfig(
                    provider=settings.model_provider_name,
                    model=settings.model_name,
                    revision=settings.model_revision or None,
                    endpoint=settings.model_api_endpoint,
                    api_key=settings.model_api_key.get_secret_value(),
                    timeout_seconds=settings.model_timeout_seconds,
                )
            ),
            external=True,
        )
    return registry
