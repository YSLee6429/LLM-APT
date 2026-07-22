"""HTTP adapter for the isolated execution-plane runner."""

from __future__ import annotations

import base64
from collections.abc import Sequence

import httpx

from llmapt.application.ports import CompilationResult, ExecutionResult
from llmapt.domain.errors import EvaluationError
from llmapt.domain.problems import ResourceLimits


class HttpSandbox:
    def __init__(
        self,
        endpoint: str,
        token: str,
        timeout_seconds: float = 35.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._token = token
        self._timeout = timeout_seconds
        self._transport = transport

    async def compile(
        self,
        source: bytes,
        language: str,
        limits: ResourceLimits,
    ) -> CompilationResult:
        payload = {
            "source_base64": base64.b64encode(source).decode("ascii"),
            "language": language,
            "limits": _limits_payload(limits),
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(
                    f"{self._endpoint}/v1/compile",
                    json=payload,
                    headers={"X-Runner-Token": self._token},
                )
            response.raise_for_status()
            data = response.json()
            return CompilationResult(
                succeeded=bool(data["succeeded"]),
                artifact_token=data.get("artifact_token"),
                diagnostics=base64.b64decode(data["diagnostics_base64"], validate=True),
                duration_ms=int(data["duration_ms"]),
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise EvaluationError("runner compilation request failed") from exc

    async def execute(
        self,
        artifact_token: str,
        arguments: Sequence[str],
        standard_input: bytes,
        limits: ResourceLimits,
    ) -> ExecutionResult:
        payload = {
            "artifact_token": artifact_token,
            "arguments": list(arguments),
            "standard_input_base64": base64.b64encode(standard_input).decode("ascii"),
            "limits": _limits_payload(limits),
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.post(
                    f"{self._endpoint}/v1/execute",
                    json=payload,
                    headers={"X-Runner-Token": self._token},
                )
            response.raise_for_status()
            data = response.json()
            return ExecutionResult(
                exit_code=data.get("exit_code"),
                stdout=base64.b64decode(data["stdout_base64"], validate=True),
                stderr=base64.b64decode(data["stderr_base64"], validate=True),
                duration_ms=int(data["duration_ms"]),
                timed_out=bool(data["timed_out"]),
                memory_exceeded=bool(data["memory_exceeded"]),
                output_exceeded=bool(data["output_exceeded"]),
                infrastructure_error=bool(data["infrastructure_error"]),
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise EvaluationError("runner execution request failed") from exc


def _limits_payload(limits: ResourceLimits) -> dict[str, int]:
    return {
        "time_limit_ms": limits.time_limit_ms,
        "memory_limit_mb": limits.memory_limit_mb,
        "process_limit": limits.process_limit,
        "output_limit_bytes": limits.output_limit_bytes,
    }
