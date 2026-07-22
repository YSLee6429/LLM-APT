"""M2 deterministic mutation proposal endpoints."""

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from llmapt.api.auth import require_roles, require_user
from llmapt.api.schemas import (
    CandidateReviewRequest,
    CandidateReviewResponse,
    CandidateStateResponse,
    MutationPreviewRequest,
    MutationPreviewResponse,
    ProblemDefinition,
)
from llmapt.application.mutations import MutationService
from llmapt.application.ports import CandidateRepository, CandidateReviewRepository
from llmapt.application.reviews import CandidateReviewService
from llmapt.domain.errors import EvaluationError
from llmapt.domain.mutations import MutationCandidate
from llmapt.domain.workspace import WorkspaceRole, WorkspaceUser

router = APIRouter(
    prefix="/api/v1/mutations",
    tags=["mutations"],
    dependencies=[Depends(require_user)],
)


def _response(candidate: MutationCandidate) -> MutationPreviewResponse:
    return MutationPreviewResponse(
        candidate_id=candidate.candidate_id,
        created_at=candidate.created_at,
        operator=candidate.operator,
        parent_problem_id=candidate.parent_problem_id,
        parent_statement_digest=candidate.parent_statement_digest,
        parent_test_suite_digest=candidate.parent_test_suite_digest,
        random_seed=candidate.random_seed,
        notes=candidate.notes,
        requires_oracle_validation=candidate.requires_oracle_validation,
        problem=ProblemDefinition.from_domain(candidate.problem),
    )


def _mutate(body: MutationPreviewRequest) -> MutationCandidate:
    return MutationService().mutate(
        body.problem.to_domain(),
        body.operator,
        random_seed=body.random_seed,
        boundary_clause=body.boundary_clause,
    )


@router.post("/preview", response_model=MutationPreviewResponse)
async def preview_mutation(body: MutationPreviewRequest) -> MutationPreviewResponse:
    try:
        candidate = _mutate(body)
    except EvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _response(candidate)


@router.post(
    "/propose",
    response_model=MutationPreviewResponse,
    dependencies=[Depends(require_roles(WorkspaceRole.ADMIN, WorkspaceRole.RESEARCHER))],
)
async def propose_mutation(
    request: Request,
    body: MutationPreviewRequest,
) -> MutationPreviewResponse:
    candidates = cast(CandidateRepository, request.app.state.candidate_repository)
    try:
        candidate = _mutate(body)
        await candidates.save(candidate)
    except EvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _response(candidate)


@router.get(
    "/{candidate_id}",
    response_model=MutationPreviewResponse,
    dependencies=[Depends(require_roles(WorkspaceRole.ADMIN, WorkspaceRole.RESEARCHER))],
)
async def get_candidate(request: Request, candidate_id: UUID) -> MutationPreviewResponse:
    candidates = cast(CandidateRepository, request.app.state.candidate_repository)
    candidate = await candidates.get(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found")
    return _response(candidate)


@router.get(
    "/{candidate_id}/state",
    response_model=CandidateStateResponse,
    dependencies=[Depends(require_roles(WorkspaceRole.ADMIN, WorkspaceRole.RESEARCHER))],
)
async def get_candidate_state(request: Request, candidate_id: UUID) -> CandidateStateResponse:
    candidates = cast(CandidateRepository, request.app.state.candidate_repository)
    state_record = await candidates.get_state(candidate_id)
    if state_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate not found")
    return CandidateStateResponse(
        candidate_id=state_record.candidate_id,
        status=state_record.status,
        updated_at=state_record.updated_at,
        oracle_validation_id=state_record.oracle_validation_id,
        reason_code=state_record.reason_code,
    )


@router.post("/{candidate_id}/review", response_model=CandidateReviewResponse)
async def review_candidate(
    request: Request,
    candidate_id: UUID,
    body: CandidateReviewRequest,
    principal: Annotated[
        WorkspaceUser,
        Depends(require_roles(WorkspaceRole.ADMIN, WorkspaceRole.REVIEWER)),
    ],
) -> CandidateReviewResponse:
    candidates = cast(CandidateRepository, request.app.state.candidate_repository)
    reviews = cast(CandidateReviewRepository, request.app.state.candidate_review_repository)
    try:
        review = await CandidateReviewService(candidates, reviews).review(
            candidate_id,
            body.decision,
            principal.username,
            body.justification,
        )
    except (EvaluationError, ValueError) as exc:
        message = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if message == "mutation candidate not found"
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=status_code, detail=message) from exc
    state_record = await candidates.get_state(candidate_id)
    if state_record is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="candidate state lost")
    return CandidateReviewResponse(
        review_id=review.review_id,
        candidate_id=review.candidate_id,
        created_at=review.created_at,
        decision=review.decision,
        reviewer=review.reviewer,
        justification=review.justification,
        candidate_status=state_record.status,
    )
