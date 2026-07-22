"""Minimal C++ runner intended for an isolated, network-internal container."""

from __future__ import annotations

import base64
import os
import secrets
import shutil
import signal
import subprocess
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

WORK_ROOT = Path("/work")
ARTIFACT_ROOT = WORK_ROOT / "artifacts"
RUNNER_TOKEN = os.environ.get("LLMAPT_RUNNER_TOKEN", "local-runner-change-me")
MAX_SOURCE_BYTES = 1_048_576
MAX_INPUT_BYTES = 4_194_304
MAX_DIAGNOSTICS_BYTES = 65_536
MAX_ARTIFACTS = 128
ARTIFACT_TTL_SECONDS = 3600


class Limits(BaseModel):
    model_config = ConfigDict(frozen=True)
    time_limit_ms: int = Field(ge=1, le=30_000)
    memory_limit_mb: int = Field(ge=16, le=1024)
    process_limit: int = Field(ge=1, le=32)
    output_limit_bytes: int = Field(ge=1, le=16_777_216)


class CompileRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_base64: str
    language: str
    limits: Limits


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    artifact_token: str = Field(pattern=r"^[0-9a-f-]{36}$")
    arguments: tuple[str, ...] = Field(max_length=16)
    standard_input_base64: str
    limits: Limits


def authorize(x_runner_token: str = Header(default="")) -> None:
    if not secrets.compare_digest(x_runner_token, RUNNER_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@asynccontextmanager
async def runner_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="LLM-APT Runner",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=runner_lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/compile", dependencies=[Depends(authorize)])
def compile_source(body: CompileRequest) -> dict[str, object]:
    if body.language.casefold() not in {"cpp", "c++", "cpp20"}:
        raise HTTPException(status_code=422, detail="unsupported language")
    try:
        source = base64.b64decode(body.source_base64, validate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid source encoding") from exc
    if not source or len(source) > MAX_SOURCE_BYTES:
        raise HTTPException(status_code=422, detail="invalid source size")

    _prune_artifacts()
    token = str(uuid4())
    artifact_dir = ARTIFACT_ROOT / token
    artifact_dir.mkdir(mode=0o700)
    source_path = artifact_dir / "main.cpp"
    binary_path = artifact_dir / "program"
    source_path.write_bytes(source)
    started = time.monotonic()
    try:
        result = subprocess.run(
            ["g++", "-std=c++20", "-O2", "-pipe", str(source_path), "-o", str(binary_path)],
            capture_output=True,
            timeout=min(30, max(5, body.limits.time_limit_ms / 1000 * 5)),
            check=False,
        )
        diagnostics = (result.stdout + result.stderr)[:MAX_DIAGNOSTICS_BYTES]
        succeeded = result.returncode == 0 and binary_path.is_file()
    except subprocess.TimeoutExpired as exc:
        diagnostics = ((exc.stdout or b"") + (exc.stderr or b"") + b"compiler timeout")[
            :MAX_DIAGNOSTICS_BYTES
        ]
        succeeded = False
    duration_ms = max(1, int((time.monotonic() - started) * 1000))
    if not succeeded:
        binary_path.unlink(missing_ok=True)
    return {
        "succeeded": succeeded,
        "artifact_token": token if succeeded else None,
        "diagnostics_base64": base64.b64encode(diagnostics).decode("ascii"),
        "duration_ms": duration_ms,
    }


def _prune_artifacts() -> None:
    now = time.time()
    directories = sorted(
        (path for path in ARTIFACT_ROOT.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
    )
    for index, path in enumerate(directories):
        expired = now - path.stat().st_mtime > ARTIFACT_TTL_SECONDS
        over_limit = index < max(0, len(directories) - MAX_ARTIFACTS + 1)
        if expired or over_limit:
            shutil.rmtree(path, ignore_errors=True)


def _detect_memory_exceeded(
    stderr: bytes,
    peak_memory_kb: int,
    memory_limit_kb: int,
    timed_out: bool,
) -> bool:
    memory_signature = b"bad_alloc" in stderr or b"cannot allocate memory" in stderr.lower()
    return not timed_out and (peak_memory_kb >= int(memory_limit_kb * 0.95) or memory_signature)


@app.post("/v1/execute", dependencies=[Depends(authorize)])
def execute_artifact(body: ExecuteRequest) -> dict[str, object]:
    binary_path = ARTIFACT_ROOT / body.artifact_token / "program"
    if not binary_path.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    if any(len(argument) > 1024 for argument in body.arguments):
        raise HTTPException(status_code=422, detail="argument too long")
    try:
        standard_input = base64.b64decode(body.standard_input_base64, validate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid input encoding") from exc
    if len(standard_input) > MAX_INPUT_BYTES:
        raise HTTPException(status_code=422, detail="input too large")

    run_dir = WORK_ROOT / f"run-{uuid4()}"
    run_dir.mkdir(mode=0o700)
    stdout_path = run_dir / "stdout"
    stderr_path = run_dir / "stderr"
    usage_path = run_dir / "usage"
    started = time.monotonic()
    timed_out = False
    infrastructure_error = False
    return_code: int | None = None
    process: subprocess.Popen[bytes] | None = None
    try:
        memory_bytes = body.limits.memory_limit_mb * 1024 * 1024
        cpu_seconds = max(1, (body.limits.time_limit_ms + 999) // 1000)
        command = [
            "/usr/bin/time",
            "-f",
            "%M",
            "-o",
            str(usage_path),
            "prlimit",
            f"--as={memory_bytes}:{memory_bytes}",
            f"--cpu={cpu_seconds}:{cpu_seconds + 1}",
            f"--nproc={body.limits.process_limit}:{body.limits.process_limit}",
            f"--fsize={body.limits.output_limit_bytes}:{body.limits.output_limit_bytes}",
            "--core=0:0",
            "--",
            str(binary_path),
            *body.arguments,
        ]
        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=run_dir,
                start_new_session=True,
            )
            try:
                process.communicate(
                    input=standard_input,
                    timeout=body.limits.time_limit_ms / 1000,
                )
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=2)
            return_code = process.returncode
    except (OSError, subprocess.SubprocessError):
        infrastructure_error = True
    finally:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=2)
            except (OSError, subprocess.SubprocessError):
                infrastructure_error = True

    stdout = stdout_path.read_bytes()[: body.limits.output_limit_bytes + 1]
    stderr = stderr_path.read_bytes()[: body.limits.output_limit_bytes + 1]
    output_exceeded = (
        len(stdout) > body.limits.output_limit_bytes
        or len(stderr) > body.limits.output_limit_bytes
        or return_code == -signal.SIGXFSZ
    )
    try:
        peak_memory_kb = int(usage_path.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        peak_memory_kb = 0
    memory_limit_kb = body.limits.memory_limit_mb * 1024
    memory_exceeded = _detect_memory_exceeded(
        stderr,
        peak_memory_kb,
        memory_limit_kb,
        timed_out,
    )
    stdout = stdout[: body.limits.output_limit_bytes]
    stderr = stderr[: body.limits.output_limit_bytes]
    duration_ms = max(1, int((time.monotonic() - started) * 1000))
    shutil.rmtree(run_dir, ignore_errors=True)
    return {
        "exit_code": return_code,
        "stdout_base64": base64.b64encode(stdout).decode("ascii"),
        "stderr_base64": base64.b64encode(stderr).decode("ascii"),
        "duration_ms": duration_ms,
        "timed_out": timed_out,
        "memory_exceeded": memory_exceeded,
        "output_exceeded": output_exceeded,
        "infrastructure_error": infrastructure_error,
    }
