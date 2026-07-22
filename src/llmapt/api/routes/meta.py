"""Service metadata endpoint."""

from fastapi import APIRouter, Request

from llmapt.api.schemas import ServiceInfo

router = APIRouter(prefix="/api/v1", tags=["metadata"])


@router.get("/", response_model=ServiceInfo)
async def service_info(request: Request) -> ServiceInfo:
    settings = request.app.state.settings
    return ServiceInfo(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment.value,
    )
