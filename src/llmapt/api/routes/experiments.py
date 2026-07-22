"""M2 experiment planning endpoints."""

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from llmapt.api.auth import require_roles
from llmapt.api.schemas import (
    ExperimentDispatchResponse,
    ExperimentPlanRequest,
    ExperimentPlanResponse,
    ExperimentStateResponse,
    ModelIdentityResponse,
)
from llmapt.application.dispatch import ExperimentDispatchService
from llmapt.application.experiments import ExperimentPlanner, PlanExperimentRequest
from llmapt.application.ports import ExperimentRepository, ExperimentScheduler
from llmapt.application.provider_registry import ProviderNotFoundError, ProviderRegistry
from llmapt.domain.errors import EvaluationError, InvalidTransitionError
from llmapt.domain.experiments import ExperimentManifest
from llmapt.domain.workspace import WorkspaceRole

router = APIRouter(
    prefix="/api/v1/experiments",
    tags=["experiments"],
    dependencies=[Depends(require_roles(WorkspaceRole.ADMIN, WorkspaceRole.RESEARCHER))],
)


def _response(
    manifest: ExperimentManifest,
    *,
    ephemeral_storage: bool,
) -> ExperimentPlanResponse:
    return ExperimentPlanResponse(
        experiment_id=manifest.experiment_id,
        created_at=manifest.created_at,
        problem_id=manifest.problem_id,
        statement_digest=manifest.statement_digest,
        test_suite_digest=manifest.test_suite_digest,
        target=ModelIdentityResponse(
            provider=manifest.target.provider,
            model=manifest.target.model,
            revision=manifest.target.revision,
        ),
        prompt_template_version=manifest.prompt_template_version,
        random_seed=manifest.random_seed,
        repetitions=manifest.repetitions,
        parameters=dict(manifest.parameters),
        plan_digest=manifest.plan_digest,
        ephemeral_storage=ephemeral_storage,
    )


@router.post("/plan", response_model=ExperimentPlanResponse)
async def plan_experiment(request: Request, body: ExperimentPlanRequest) -> ExperimentPlanResponse:
    registry = cast(ProviderRegistry, request.app.state.provider_registry)
    experiments = cast(ExperimentRepository, request.app.state.experiment_repository)
    try:
        manifest = await ExperimentPlanner(registry, experiments).plan(
            PlanExperimentRequest(
                problem=body.problem.to_domain(),
                provider_key=body.provider_key,
                prompt_template_version=body.prompt_template_version,
                random_seed=body.random_seed,
                repetitions=body.repetitions,
                parameters=body.parameters,
            )
        )
    except ProviderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return _response(
        manifest,
        ephemeral_storage=cast(bool, request.app.state.experiment_storage_ephemeral),
    )


@router.get("/{experiment_id}", response_model=ExperimentPlanResponse)
async def get_experiment(request: Request, experiment_id: UUID) -> ExperimentPlanResponse:
    experiments = cast(ExperimentRepository, request.app.state.experiment_repository)
    manifest = await experiments.get(experiment_id)
    if manifest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="experiment not found")
    return _response(
        manifest,
        ephemeral_storage=cast(bool, request.app.state.experiment_storage_ephemeral),
    )


@router.get("/{experiment_id}/state", response_model=ExperimentStateResponse)
async def get_experiment_state(
    request: Request,
    experiment_id: UUID,
) -> ExperimentStateResponse:
    experiments = cast(ExperimentRepository, request.app.state.experiment_repository)
    state_record = await experiments.get_state(experiment_id)
    if state_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="experiment not found")
    return ExperimentStateResponse(
        experiment_id=state_record.experiment_id,
        status=state_record.status,
        updated_at=state_record.updated_at,
        task_id=state_record.task_id,
        last_error=state_record.last_error,
    )


@router.post("/{experiment_id}/enqueue", response_model=ExperimentDispatchResponse)
async def enqueue_experiment(
    request: Request,
    experiment_id: UUID,
) -> ExperimentDispatchResponse:
    experiments = cast(ExperimentRepository, request.app.state.experiment_repository)
    scheduler = cast(ExperimentScheduler, request.app.state.experiment_scheduler)
    try:
        receipt = await ExperimentDispatchService(experiments, scheduler).enqueue(experiment_id)
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except EvaluationError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if str(exc) == "experiment not found"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return ExperimentDispatchResponse(
        experiment_id=receipt.experiment_id,
        task_id=receipt.task_id,
        status=receipt.state.status,
    )
