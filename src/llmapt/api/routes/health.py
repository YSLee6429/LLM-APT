"""Liveness and readiness probes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response, status

from llmapt.api.schemas import HealthResponse, ReadinessResponse

router = APIRouter(tags=["system"])


@router.get("/health/live", response_model=HealthResponse)
async def liveness(request: Request) -> HealthResponse:
    """Report that the API process can serve requests."""

    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        checked_at=datetime.now(UTC),
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    """Report whether every control-plane dependency is currently reachable."""

    settings = request.app.state.settings
    components = dict(await request.app.state.readiness_probe.check())
    ready = all(value == "ready" for value in components.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        service=settings.app_name,
        version=settings.app_version,
        checked_at=datetime.now(UTC),
        components=components,
    )
