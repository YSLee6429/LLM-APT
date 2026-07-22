import httpx
import pytest

from llmapt.config import Settings
from llmapt.infrastructure.readiness import InfrastructureReadinessProbe


class _FakeClient:
    def __init__(self, *, status_code: int = 200, raises: bool = False, **_kwargs: object) -> None:
        self._status_code = status_code
        self._raises = raises

    async def __aenter__(self):  # type: ignore[no-untyped-def]
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def get(self, _url: str) -> httpx.Response:
        if self._raises:
            raise httpx.ConnectError("offline")
        return httpx.Response(self._status_code)


@pytest.mark.asyncio
async def test_runner_readiness_success_and_failure(
    monkeypatch: pytest.MonkeyPatch,
    test_settings: Settings,
) -> None:
    probe = InfrastructureReadinessProbe(test_settings)
    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
    assert await probe._runner() is True

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _FakeClient(raises=True, **kwargs),
    )
    assert await probe._runner() is False
