"""HTTP adapter for providers implementing the OpenAI-compatible chat contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from llmapt.application.ports import ModelRequest, ModelResponse
from llmapt.domain.entities import ModelIdentity
from llmapt.domain.errors import EvaluationError

_ALLOWED_PARAMETERS = frozenset(
    {
        "temperature",
        "top_p",
        "max_tokens",
        "seed",
        "frequency_penalty",
        "presence_penalty",
        "stop",
    }
)


class ProviderTransportError(EvaluationError):
    """External provider could not return a valid generation response."""


@dataclass(frozen=True, slots=True)
class OpenAICompatibleConfig:
    provider: str
    model: str
    endpoint: str
    api_key: str
    revision: str | None = None
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.model.strip():
            raise ValueError("provider and model must not be blank")
        if not self.endpoint.startswith(("https://", "http://")):
            raise ValueError("endpoint must be an absolute HTTP(S) URL")
        if not self.api_key:
            raise ValueError("api_key must not be blank")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


class OpenAICompatibleProvider:
    def __init__(
        self,
        config: OpenAICompatibleConfig,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._client = client

    async def identify(self) -> ModelIdentity:
        return ModelIdentity(
            provider=self._config.provider,
            model=self._config.model,
            revision=self._config.revision,
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        unsupported = sorted(set(request.parameters) - _ALLOWED_PARAMETERS)
        if unsupported:
            raise EvaluationError(f"unsupported model parameters: {', '.join(unsupported)}")

        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": False,
            **request.parameters,
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._config.timeout_seconds)
        try:
            response = await client.post(self._config.endpoint, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderTransportError("model provider request failed") from exc
        finally:
            if owns_client:
                await client.aclose()

        if response.status_code == 401 or response.status_code == 403:
            raise ProviderTransportError("model provider rejected the configured credential")
        if response.status_code == 429:
            raise ProviderTransportError("model provider rate limit exceeded")
        if response.is_error:
            raise ProviderTransportError(f"model provider returned HTTP {response.status_code}")

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderTransportError(
                "model provider returned an invalid response schema"
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise ProviderTransportError("model provider returned empty source content")

        usage = body.get("usage", {})
        input_tokens = self._optional_int(usage, "prompt_tokens")
        output_tokens = self._optional_int(usage, "completion_tokens")
        return ModelResponse(
            identity=await self.identify(),
            raw_text=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    @staticmethod
    def _optional_int(mapping: object, key: str) -> int | None:
        if not isinstance(mapping, dict):
            return None
        value = mapping.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else None
