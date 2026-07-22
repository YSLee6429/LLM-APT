"""Authenticated M3 dashboard projections."""

from collections import Counter
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from llmapt.api.auth import require_user
from llmapt.api.m3_schemas import (
    CandidateSummaryResponse,
    DashboardResponse,
    EvidenceSummaryResponse,
    ExperimentSummaryResponse,
)
from llmapt.application.ports import (
    CandidateRepository,
    ClosedLoopRepository,
    ExperimentRepository,
    WorkspaceRepository,
)
from llmapt.domain.closed_loop import ClosedLoopReport
from llmapt.domain.workspace import WorkspaceRole, WorkspaceUser

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def evidence_summary(report: ClosedLoopReport) -> EvidenceSummaryResponse:
    return EvidenceSummaryResponse(
        report_id=report.report_id,
        candidate_id=report.candidate_id,
        created_at=report.created_at,
        provider=report.target.provider,
        model=report.target.model,
        verdict=report.verdict,
        evidence_level=report.evidence_level,
        stable_failure=report.stable_failure,
        repetitions_completed=report.repetitions_completed,
        has_counterexample=report.counterexample is not None,
    )


@router.get("", response_model=DashboardResponse)
async def dashboard(
    request: Request,
    user: Annotated[WorkspaceUser, Depends(require_user)],
) -> DashboardResponse:
    workspace = cast(WorkspaceRepository, request.app.state.workspace_repository)
    owner_id = None if user.role is WorkspaceRole.ADMIN else user.user_id
    projects = await workspace.list_projects(owner_id)
    profiles = [
        profile
        for project in projects
        for profile in await workspace.list_model_profiles(project.project_id)
    ]
    if user.role is WorkspaceRole.GUEST:
        return DashboardResponse(
            projects=len(projects),
            model_profiles=len(profiles),
            experiments=0,
            candidates=0,
            evidence_reports=0,
            stable_failures=0,
            verdict_counts={},
            experiment_status_counts={},
            candidate_status_counts={},
            recent_experiments=(),
            recent_evidence=(),
        )
    experiments = await cast(
        ExperimentRepository, request.app.state.experiment_repository
    ).list_recent(500)
    candidates = await cast(
        CandidateRepository, request.app.state.candidate_repository
    ).list_recent(500)
    reports = await cast(
        ClosedLoopRepository, request.app.state.closed_loop_repository
    ).list_recent(500)
    return DashboardResponse(
        projects=len(projects),
        model_profiles=len(profiles),
        experiments=len(experiments),
        candidates=len(candidates),
        evidence_reports=len(reports),
        stable_failures=sum(1 for item in reports if item.stable_failure),
        verdict_counts=dict(Counter(item.verdict.value for item in reports)),
        experiment_status_counts=dict(Counter(state.status.value for _, state in experiments)),
        candidate_status_counts=dict(Counter(state.status.value for _, state in candidates)),
        recent_experiments=tuple(
            ExperimentSummaryResponse(
                experiment_id=manifest.experiment_id,
                created_at=manifest.created_at,
                problem_id=manifest.problem_id,
                provider=manifest.target.provider,
                model=manifest.target.model,
                status=state.status,
                repetitions=manifest.repetitions,
                plan_digest=manifest.plan_digest,
            )
            for manifest, state in experiments[:10]
        ),
        recent_evidence=tuple(evidence_summary(item) for item in reports[:10]),
    )


@router.get("/experiments", response_model=tuple[ExperimentSummaryResponse, ...])
async def experiment_list(
    request: Request,
    user: Annotated[WorkspaceUser, Depends(require_user)],
) -> tuple[ExperimentSummaryResponse, ...]:
    if user.role is WorkspaceRole.GUEST:
        return ()
    items = await cast(ExperimentRepository, request.app.state.experiment_repository).list_recent(
        200
    )
    return tuple(
        ExperimentSummaryResponse(
            experiment_id=manifest.experiment_id,
            created_at=manifest.created_at,
            problem_id=manifest.problem_id,
            provider=manifest.target.provider,
            model=manifest.target.model,
            status=state.status,
            repetitions=manifest.repetitions,
            plan_digest=manifest.plan_digest,
        )
        for manifest, state in items
    )


@router.get("/candidates", response_model=tuple[CandidateSummaryResponse, ...])
async def candidate_list(
    request: Request,
    user: Annotated[WorkspaceUser, Depends(require_user)],
) -> tuple[CandidateSummaryResponse, ...]:
    if user.role is WorkspaceRole.GUEST:
        return ()
    items = await cast(CandidateRepository, request.app.state.candidate_repository).list_recent(200)
    return tuple(
        CandidateSummaryResponse(
            candidate_id=candidate.candidate_id,
            created_at=candidate.created_at,
            parent_problem_id=candidate.parent_problem_id,
            operator=candidate.operator.value,
            status=state.status,
            oracle_validation_id=state.oracle_validation_id,
        )
        for candidate, state in items
    )
