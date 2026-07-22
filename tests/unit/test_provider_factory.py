import pytest

from llmapt.config import Environment, Settings
from llmapt.infrastructure.providers.factory import build_provider_registry


@pytest.mark.asyncio
async def test_factory_registers_external_provider_only_when_enabled() -> None:
    settings = Settings(
        environment=Environment.TEST,
        external_model_calls_enabled=True,
        model_provider_key="compatible",
        model_provider_name="test-provider",
        model_name="coder-model",
        model_api_endpoint="https://provider.invalid/v1/chat/completions",
        model_api_key="secret",
    )

    descriptors = await build_provider_registry(settings).describe()

    assert [item.key for item in descriptors] == ["compatible", "local"]
    assert descriptors[0].external is True
    assert descriptors[0].identity.model == "coder-model"


def test_factory_requires_complete_external_configuration() -> None:
    with pytest.raises(ValueError, match="model_name"):
        build_provider_registry(Settings(external_model_calls_enabled=True))


def test_factory_requires_https_in_production() -> None:
    settings = Settings(
        environment=Environment.PRODUCTION,
        runner_token="production-runner-token",
        auth_secret="production-auth-secret",
        bootstrap_admin_password="production-admin-password",
        external_model_calls_enabled=True,
        model_name="coder-model",
        model_api_endpoint="http://provider.invalid/v1/chat/completions",
        model_api_key="secret",
    )

    with pytest.raises(ValueError, match="must use HTTPS"):
        build_provider_registry(settings)
