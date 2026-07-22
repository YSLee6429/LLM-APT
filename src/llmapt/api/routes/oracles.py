"""Trusted oracle catalog and mutation validation endpoints."""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request, status

from llmapt.api.auth import require_roles, require_user
from llmapt.api.schemas import (
    OracleCaseValidationResponse,
    OracleIdentityResponse,
    OracleValidationRequest,
    OracleValidationResponse,
)
from llmapt.application.oracle_registry import OracleRegistry
from llmapt.application.oracle_validation import OracleValidationService
from llmapt.application.ports import CandidateRepository, OracleValidationRepository
from llmapt.domain.errors import EvaluationError
from llmapt.domain.oracles import OracleIdentity, OracleValidationReport
from llmapt.domain.workspace import WorkspaceRole

router = APIRouter(
    prefix="/api/v1/oracles",
    tags=["oracles"],
    dependencies=[Depends(require_user)],
)


def _identity_response(identity: OracleIdentity) -> OracleIdentityResponse:
    return OracleIdentityResponse(
        key=identity.key,
        version=identity.version,
        parent_problem_id=identity.parent_problem_id,
        parent_statement_digest=identity.parent_statement_digest,
        language=identity.language,
    )


def _report_response(report: OracleValidationReport) -> OracleValidationResponse:
    return OracleValidationResponse(
        validation_id=report.validation_id,
        candidate_id=report.candidate_id,
        created_at=report.created_at,
        oracle=_identity_response(report.oracle),
        candidate_statement_digest=report.candidate_statement_digest,
        candidate_test_suite_digest=report.candidate_test_suite_digest,
        verdict=report.verdict,
        cases=tuple(
            OracleCaseValidationResponse(
                case_id=case.case_id,
                input_digest=case.input_digest,
                expected_output_digest=case.expected_output_digest,
                actual_output_digest=case.actual_output_digest,
                matched=case.matched,
                reason_code=case.reason_code,
            )
            for case in report.cases
        ),
        passed_cases=report.passed_cases,
        total_cases=len(report.cases),
        reason_code=report.reason_code,
    )


@router.get("", response_model=tuple[OracleIdentityResponse, ...])
async def list_oracles(request: Request) -> tuple[OracleIdentityResponse, ...]:
    registry = cast(OracleRegistry, request.app.state.oracle_registry)
    return tuple(_identity_response(identity) for identity in registry.catalog())


@router.post(
    "/validate",
    response_model=OracleValidationResponse,
    dependencies=[Depends(require_roles(WorkspaceRole.ADMIN, WorkspaceRole.RESEARCHER))],
)
async def validate_candidate(
    request: Request,
    body: OracleValidationRequest,
) -> OracleValidationResponse:
    candidates = cast(CandidateRepository, request.app.state.candidate_repository)
    validations = cast(
        OracleValidationRepository,
        request.app.state.oracle_validation_repository,
    )
    registry = cast(OracleRegistry, request.app.state.oracle_registry)
    try:
        report = await OracleValidationService(candidates, validations, registry).validate(
            body.candidate_id,
            body.oracle_key,
        )
    except EvaluationError as exc:
        message = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if message in {"mutation candidate not found", "trusted oracle not found"}
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=status_code, detail=message) from exc
    return _report_response(report)
