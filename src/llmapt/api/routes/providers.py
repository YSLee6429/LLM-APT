"""M2 provider discovery and controlled generation endpoints."""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request, status

from llmapt.api.auth import require_roles, require_user
from llmapt.api.schemas import (
    GenerationRequest,
    GenerationResponse,
    ModelIdentityResponse,
    ProviderResponse,
)
from llmapt.application.ports import ModelRequest
from llmapt.application.provider_registry import ProviderNotFoundError, ProviderRegistry
from llmapt.application.source_extraction import extract_candidate_source
from llmapt.domain.digests import digest_text
from llmapt.domain.errors import EvaluationError
from llmapt.domain.workspace import WorkspaceRole
from llmapt.infrastructure.providers.openai_compatible import ProviderTransportError

router = APIRouter(
    prefix="/api/v1/providers",
    tags=["providers"],
    dependencies=[Depends(require_user)],
)


def _registry(request: Request) -> ProviderRegistry:
    return cast(ProviderRegistry, request.app.state.provider_registry)


def _identity_response(provider: str, model: str, revision: str | None) -> ModelIdentityResponse:
    return ModelIdentityResponse(provider=provider, model=model, revision=revision)


@router.get("", response_model=tuple[ProviderResponse, ...])
async def list_providers(request: Request) -> tuple[ProviderResponse, ...]:
    descriptors = await _registry(request).describe()
    return tuple(
        ProviderResponse(
            key=descriptor.key,
            identity=_identity_response(
                descriptor.identity.provider,
                descriptor.identity.model,
                descriptor.identity.revision,
            ),
            external=descriptor.external,
        )
        for descriptor in descriptors
    )


@router.post(
    "/generate",
    response_model=GenerationResponse,
    dependencies=[Depends(require_roles(WorkspaceRole.ADMIN, WorkspaceRole.RESEARCHER))],
)
async def generate_candidate(request: Request, body: GenerationRequest) -> GenerationResponse:
    try:
        response = await _registry(request).generate(
            body.provider_key,
            ModelRequest(
                prompt=body.prompt,
                language=body.language,
                parameters=body.parameters,
            ),
        )
        extracted = extract_candidate_source(response.raw_text, body.language)
    except ProviderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProviderTransportError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except EvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return GenerationResponse(
        identity=_identity_response(
            response.identity.provider,
            response.identity.model,
            response.identity.revision,
        ),
        source=extracted.source,
        raw_response_digest=digest_text(response.raw_text),
        source_digest=digest_text(extracted.source),
        extracted_from_fence=extracted.used_fence,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
    )
