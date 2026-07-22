"""M1 deterministic evaluation demonstration endpoint."""

from fastapi import APIRouter, Depends

from llmapt.api.auth import require_user
from llmapt.api.schemas import (
    CaseEvaluationResponse,
    MockEvaluationRequest,
    MockEvaluationResponse,
)
from llmapt.demo import run_mock_scenario

router = APIRouter(
    prefix="/api/v1/evaluations",
    tags=["evaluations"],
    dependencies=[Depends(require_user)],
)


@router.post("/mock", response_model=MockEvaluationResponse)
async def mock_evaluation(request: MockEvaluationRequest) -> MockEvaluationResponse:
    """Exercise M1 without a model API key or untrusted source execution."""

    report = await run_mock_scenario(request.scenario, request.random_seed)
    return MockEvaluationResponse(
        run_id=str(report.run_id),
        problem_id=report.problem_id,
        verdict=report.verdict,
        evidence_level=report.evidence_level,
        passed_cases=report.passed_cases,
        total_cases=report.total_cases,
        cases=tuple(
            CaseEvaluationResponse(
                case_id=case.case_id,
                verdict=case.verdict,
                duration_ms=case.duration_ms,
                input_digest=case.input_digest,
                expected_output_digest=case.expected_output_digest,
                actual_output_digest=case.actual_output_digest,
            )
            for case in report.cases
        ),
    )
