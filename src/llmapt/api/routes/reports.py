"""Evidence review and deterministic report exports for M3."""

from __future__ import annotations

import csv
import io
import json
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from llmapt.api.auth import require_roles, require_user
from llmapt.api.m3_schemas import EvidenceSummaryResponse
from llmapt.api.routes.closed_loop import _response
from llmapt.api.schemas import ClosedLoopReportResponse
from llmapt.application.ports import ClosedLoopRepository, WorkspaceRepository
from llmapt.domain.closed_loop import ClosedLoopReport
from llmapt.domain.workspace import WorkspaceRole, WorkspaceUser

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _summary(report: ClosedLoopReport) -> EvidenceSummaryResponse:
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


@router.get("", response_model=tuple[EvidenceSummaryResponse, ...])
async def list_reports(
    request: Request,
    user: Annotated[WorkspaceUser, Depends(require_user)],
    project_id: UUID | None = None,
) -> tuple[EvidenceSummaryResponse, ...]:
    if user.role is WorkspaceRole.GUEST:
        return ()
    reports = await cast(
        ClosedLoopRepository, request.app.state.closed_loop_repository
    ).list_recent(200)
    if project_id is not None:
        workspace = cast(WorkspaceRepository, request.app.state.workspace_repository)
        report_ids = {
            item.resource_id
            for item in await workspace.list_resources(project_id)
            if item.resource_type == "report"
        }
        reports = [item for item in reports if item.report_id in report_ids]
    return tuple(_summary(item) for item in reports)


@router.get(
    "/{report_id}",
    response_model=ClosedLoopReportResponse,
    dependencies=[
        Depends(
            require_roles(
                WorkspaceRole.ADMIN,
                WorkspaceRole.RESEARCHER,
                WorkspaceRole.REVIEWER,
                WorkspaceRole.VIEWER,
            )
        )
    ],
)
async def report_detail(
    request: Request,
    report_id: UUID,
    _user: Annotated[WorkspaceUser, Depends(require_user)],
) -> ClosedLoopReportResponse:
    report = await cast(ClosedLoopRepository, request.app.state.closed_loop_repository).get(
        report_id
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report not found")
    return _response(report)


@router.get(
    "/{report_id}/export",
    dependencies=[
        Depends(
            require_roles(
                WorkspaceRole.ADMIN,
                WorkspaceRole.RESEARCHER,
                WorkspaceRole.REVIEWER,
                WorkspaceRole.VIEWER,
            )
        )
    ],
)
async def export_report(
    request: Request,
    report_id: UUID,
    _user: Annotated[WorkspaceUser, Depends(require_user)],
    export_format: Literal["json", "markdown", "csv"] = Query(default="json", alias="format"),
) -> Response:
    report = await cast(ClosedLoopRepository, request.app.state.closed_loop_repository).get(
        report_id
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="report not found")
    public = _response(report)
    filename = (
        f"llm-apt-report-{report_id}.{export_format if export_format != 'markdown' else 'md'}"
    )
    if export_format == "json":
        content = json.dumps(public.model_dump(mode="json"), ensure_ascii=False, indent=2)
        media_type = "application/json"
    elif export_format == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            [
                "report_id",
                "candidate_id",
                "provider",
                "model",
                "verdict",
                "evidence_level",
                "stable_failure",
                "repetitions",
            ]
        )
        writer.writerow(
            [
                report.report_id,
                report.candidate_id,
                report.target.provider,
                report.target.model,
                report.verdict.value,
                int(report.evidence_level),
                str(report.stable_failure).lower(),
                report.repetitions_completed,
            ]
        )
        content = stream.getvalue()
        media_type = "text/csv"
    else:
        counterexample = "none"
        if report.counterexample is not None:
            counterexample = (
                f"{report.counterexample.case_id}: {report.counterexample.original_size} B → "
                f"{report.counterexample.minimized_size} B"
            )
        content = "\n".join(
            [
                "# LLM-APT Evidence Report",
                "",
                f"- Report ID: `{report.report_id}`",
                f"- Candidate ID: `{report.candidate_id}`",
                f"- Target: `{report.target.provider}/{report.target.model}`",
                f"- Verdict: **{report.verdict.value}**",
                f"- Evidence level: **L{int(report.evidence_level)}**",
                f"- Stable failure: **{str(report.stable_failure).lower()}**",
                f"- Repetitions: **{report.repetitions_completed}/{report.repetitions_requested}**",
                f"- Counterexample: {counterexample}",
                "",
                "The export contains the public evidence projection only. Hidden input, generated "
                "source, raw model response and runner artifact tokens are omitted.",
            ]
        )
        media_type = "text/markdown"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
