"""Problem schema validation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from llmapt.api.auth import require_user
from llmapt.api.schemas import ProblemDefinition, ProblemValidationResponse
from llmapt.domain.errors import InvalidProblemError

router = APIRouter(
    prefix="/api/v1/problems",
    tags=["problems"],
    dependencies=[Depends(require_user)],
)


@router.post("/validate", response_model=ProblemValidationResponse)
async def validate_problem(definition: ProblemDefinition) -> ProblemValidationResponse:
    """Validate a JSON problem definition without storing or executing it."""

    try:
        problem = definition.to_domain()
    except InvalidProblemError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return ProblemValidationResponse(
        problem_id=problem.problem_id,
        test_count=len(problem.tests),
        statement_digest=problem.statement_digest,
        test_suite_digest=problem.test_suite_digest,
    )
