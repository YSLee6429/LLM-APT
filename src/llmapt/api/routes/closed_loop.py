"""M2 closed-loop execution and evidence endpoints."""

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from llmapt.api.auth import require_roles
from llmapt.api.schemas import (
    ClosedLoopReportResponse,
    ClosedLoopRunRequest,
    CounterexampleResponse,
    ModelIdentityResponse,
    RepetitionObservationResponse,
)
from llmapt.application.closed_loop import ClosedLoopRequest, ClosedLoopService
from llmapt.application.oracle_registry import OracleRegistry
from llmapt.application.ports import (
    CandidateRepository,
    ClosedLoopRepository,
    OracleValidationRepository,
    Sandbox,
)
from llmapt.application.provider_registry import ProviderRegistry
from llmapt.domain.closed_loop import ClosedLoopReport
from llmapt.domain.errors import EvaluationError
from llmapt.domain.workspace import WorkspaceRole

router = APIRouter(
    prefix="/api/v1/closed-loop",
    tags=["closed-loop"],
    dependencies=[Depends(require_roles(WorkspaceRole.ADMIN, WorkspaceRole.RESEARCHER))],
)


def _response(report: ClosedLoopReport) -> ClosedLoopReportResponse:
    return ClosedLoopReportResponse(
        report_id=report.report_id,
        candidate_id=report.candidate_id,
        oracle_validation_id=report.oracle_validation_id,
        created_at=report.created_at,
        target=ModelIdentityResponse(
            provider=report.target.provider,
            model=report.target.model,
            revision=report.target.revision,
        ),
        repetitions_requested=report.repetitions_requested,
        repetitions_completed=report.repetitions_completed,
        verdict=report.verdict,
        evidence_level=report.evidence_level,
        stable_failure=report.stable_failure,
        observations=tuple(
            RepetitionObservationResponse(
                repetition=item.repetition,
                source_digest=item.source_digest,
                raw_response_digest=item.raw_response_digest,
                verdict=item.verdict,
                failure_case_id=item.failure_case_id,
                input_digest=item.input_digest,
                expected_output_digest=item.expected_output_digest,
                actual_output_digest=item.actual_output_digest,
            )
            for item in report.observations
        ),
        counterexample=None
        if report.counterexample is None
        else CounterexampleResponse(
            case_id=report.counterexample.case_id,
            original_input_digest=report.counterexample.original_input_digest,
            minimized_input_digest=report.counterexample.minimized_input_digest,
            expected_output_digest=report.counterexample.expected_output_digest,
            actual_output_digest=report.counterexample.actual_output_digest,
            original_size=report.counterexample.original_size,
            minimized_size=report.counterexample.minimized_size,
            attempts=report.counterexample.attempts,
        ),
    )


def _service(request: Request) -> ClosedLoopService:
    return ClosedLoopService(
        cast(CandidateRepository, request.app.state.candidate_repository),
        cast(OracleValidationRepository, request.app.state.oracle_validation_repository),
        cast(ClosedLoopRepository, request.app.state.closed_loop_repository),
        cast(ProviderRegistry, request.app.state.provider_registry),
        cast(OracleRegistry, request.app.state.oracle_registry),
        cast(Sandbox, request.app.state.sandbox),
    )


@router.post("/run", response_model=ClosedLoopReportResponse)
async def run_closed_loop(
    request: Request,
    body: ClosedLoopRunRequest,
) -> ClosedLoopReportResponse:
    try:
        report = await _service(request).run(
            ClosedLoopRequest(
                candidate_id=body.candidate_id,
                oracle_key=body.oracle_key,
                provider_key=body.provider_key,
                prompt=body.prompt,
                repetitions=body.repetitions,
                parameters=body.parameters,
            )
        )
    except EvaluationError as exc:
        message = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if message in {"mutation candidate not found", "trusted oracle not found"}
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=status_code, detail=message) from exc
    return _response(report)


@router.get("/{report_id}", response_model=ClosedLoopReportResponse)
async def get_closed_loop_report(
    request: Request,
    report_id: UUID,
) -> ClosedLoopReportResponse:
    repository = cast(ClosedLoopRepository, request.app.state.closed_loop_repository)
    report = await repository.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report not found")
    return _response(report)
