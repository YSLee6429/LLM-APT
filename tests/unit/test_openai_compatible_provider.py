import json

import httpx
import pytest

from llmapt.application.ports import ModelRequest
from llmapt.domain.errors import EvaluationError
from llmapt.infrastructure.providers.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
    ProviderTransportError,
)


def _config() -> OpenAICompatibleConfig:
    return OpenAICompatibleConfig(
        provider="compatible-test",
        model="coder-test",
        revision="2026-07",
        endpoint="https://provider.invalid/v1/chat/completions",
        api_key="test-secret",
    )


@pytest.mark.asyncio
async def test_provider_sends_controlled_payload_and_parses_usage() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "```cpp\nint main() {}\n```"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 5},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleProvider(_config(), client)
        response = await provider.generate(
            ModelRequest("solve", "cpp", {"temperature": 0, "seed": 7})
        )

    assert captured["authorization"] == "Bearer test-secret"
    assert captured["payload"] == {
        "model": "coder-test",
        "messages": [{"role": "user", "content": "solve"}],
        "stream": False,
        "temperature": 0,
        "seed": 7,
    }
    assert response.identity.model == "coder-test"
    assert response.input_tokens == 12
    assert response.output_tokens == 5


@pytest.mark.asyncio
async def test_provider_rejects_parameter_injection() -> None:
    provider = OpenAICompatibleProvider(_config())

    with pytest.raises(EvaluationError, match="unsupported model parameters"):
        await provider.generate(ModelRequest("solve", "cpp", {"model": "override"}))


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
async def test_provider_classifies_remote_failures(status_code: int) -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(status_code, json={}))
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAICompatibleProvider(_config(), client)
        with pytest.raises(ProviderTransportError):
            await provider.generate(ModelRequest("solve", "cpp", {}))


@pytest.mark.asyncio
async def test_provider_rejects_malformed_success_response() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"choices": []}))
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAICompatibleProvider(_config(), client)
        with pytest.raises(ProviderTransportError, match="invalid response schema"):
            await provider.generate(ModelRequest("solve", "cpp", {}))
