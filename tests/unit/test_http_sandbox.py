import base64

import httpx
import pytest

from llmapt.domain.problems import ResourceLimits
from llmapt.infrastructure.runner import HttpSandbox


@pytest.mark.asyncio
async def test_http_sandbox_maps_compile_and_execute_responses() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Runner-Token"] == "secret"
        if request.url.path.endswith("compile"):
            return httpx.Response(
                200,
                json={
                    "succeeded": True,
                    "artifact_token": "token",
                    "diagnostics_base64": base64.b64encode(b"ok").decode(),
                    "duration_ms": 3,
                },
            )
        return httpx.Response(
            200,
            json={
                "exit_code": 0,
                "stdout_base64": base64.b64encode(b"4\n").decode(),
                "stderr_base64": "",
                "duration_ms": 2,
                "timed_out": False,
                "memory_exceeded": False,
                "output_exceeded": False,
                "infrastructure_error": False,
            },
        )

    sandbox = HttpSandbox("http://runner", "secret", transport=httpx.MockTransport(handler))
    limits = ResourceLimits(1000, 128)
    compilation = await sandbox.compile(b"int main(){}", "cpp", limits)
    execution = await sandbox.execute("token", (), b"2\n", limits)

    assert compilation.succeeded and compilation.diagnostics == b"ok"
    assert execution.stdout == b"4\n" and execution.exit_code == 0
