"""Projects, model profiles, and resource organization for M3."""

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from llmapt.api.auth import require_roles, require_user
from llmapt.api.m3_schemas import (
    ModelProfileCreateRequest,
    ModelProfileResponse,
    ProjectCreateRequest,
    ProjectResponse,
    ResourceLinkRequest,
    ResourceLinkResponse,
)
from llmapt.application.ports import (
    CandidateRepository,
    ClosedLoopRepository,
    ExperimentRepository,
    WorkspaceRepository,
)
from llmapt.domain.errors import EvaluationError
from llmapt.domain.workspace import (
    ModelProfile,
    Project,
    ProjectResource,
    WorkspaceRole,
    WorkspaceUser,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


def _project_response(project: Project, resources: int, profiles: int) -> ProjectResponse:
    return ProjectResponse(
        project_id=project.project_id,
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        resource_count=resources,
        model_profile_count=profiles,
    )


def _profile_response(profile: ModelProfile) -> ModelProfileResponse:
    return ModelProfileResponse(
        profile_id=profile.profile_id,
        project_id=profile.project_id,
        name=profile.name,
        provider=profile.provider,
        model=profile.model,
        revision=profile.revision,
        description=profile.description,
        tags=profile.tags,
        created_at=profile.created_at,
    )


def _can_access_project(user: WorkspaceUser, project: Project) -> bool:
    return user.role is WorkspaceRole.ADMIN or project.owner_id == user.user_id


async def _accessible_project(
    repository: WorkspaceRepository,
    project_id: UUID,
    user: WorkspaceUser,
) -> Project:
    project = await repository.get_project(project_id)
    if project is None or not _can_access_project(user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return project


@router.get("", response_model=tuple[ProjectResponse, ...])
async def list_projects(
    request: Request,
    user: Annotated[WorkspaceUser, Depends(require_user)],
) -> tuple[ProjectResponse, ...]:
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    owner_id = None if user.role is WorkspaceRole.ADMIN else user.user_id
    projects = await repository.list_projects(owner_id)
    responses = []
    for project in projects:
        resources = await repository.list_resources(project.project_id)
        profiles = await repository.list_model_profiles(project.project_id)
        responses.append(_project_response(project, len(resources), len(profiles)))
    return tuple(responses)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request,
    body: ProjectCreateRequest,
    user: Annotated[
        WorkspaceUser,
        Depends(
            require_roles(
                WorkspaceRole.ADMIN,
                WorkspaceRole.RESEARCHER,
                WorkspaceRole.GUEST,
            )
        ),
    ],
) -> ProjectResponse:
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    project = Project(
        name=body.name.strip(), description=body.description.strip(), owner_id=user.user_id
    )
    await repository.save_project(project)
    return _project_response(project, 0, 0)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    request: Request,
    project_id: UUID,
    user: Annotated[WorkspaceUser, Depends(require_user)],
) -> ProjectResponse:
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    project = await _accessible_project(repository, project_id, user)
    resources = await repository.list_resources(project_id)
    profiles = await repository.list_model_profiles(project_id)
    return _project_response(project, len(resources), len(profiles))


@router.get("/{project_id}/model-profiles", response_model=tuple[ModelProfileResponse, ...])
async def list_model_profiles(
    request: Request,
    project_id: UUID,
    user: Annotated[WorkspaceUser, Depends(require_user)],
) -> tuple[ModelProfileResponse, ...]:
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    await _accessible_project(repository, project_id, user)
    return tuple(
        _profile_response(item) for item in await repository.list_model_profiles(project_id)
    )


@router.post(
    "/{project_id}/model-profiles",
    response_model=ModelProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_model_profile(
    request: Request,
    project_id: UUID,
    body: ModelProfileCreateRequest,
    user: Annotated[
        WorkspaceUser,
        Depends(
            require_roles(
                WorkspaceRole.ADMIN,
                WorkspaceRole.RESEARCHER,
                WorkspaceRole.GUEST,
            )
        ),
    ],
) -> ModelProfileResponse:
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    await _accessible_project(repository, project_id, user)
    profile = ModelProfile(
        project_id=project_id,
        name=body.name.strip(),
        provider=body.provider.strip(),
        model=body.model.strip(),
        revision=None if body.revision is None else body.revision.strip() or None,
        description=body.description.strip(),
        tags=tuple(dict.fromkeys(tag.strip() for tag in body.tags if tag.strip())),
    )
    await repository.save_model_profile(profile)
    return _profile_response(profile)


@router.get("/{project_id}/resources", response_model=tuple[ResourceLinkResponse, ...])
async def list_resources(
    request: Request,
    project_id: UUID,
    user: Annotated[WorkspaceUser, Depends(require_user)],
) -> tuple[ResourceLinkResponse, ...]:
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    await _accessible_project(repository, project_id, user)
    return tuple(
        ResourceLinkResponse(
            project_id=item.project_id,
            resource_type=item.resource_type,
            resource_id=item.resource_id,
            linked_by=item.linked_by,
            linked_at=item.linked_at,
        )
        for item in await repository.list_resources(project_id)
    )


@router.post(
    "/{project_id}/resources",
    response_model=ResourceLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_resource(
    request: Request,
    project_id: UUID,
    body: ResourceLinkRequest,
    user: Annotated[
        WorkspaceUser,
        Depends(
            require_roles(
                WorkspaceRole.ADMIN,
                WorkspaceRole.RESEARCHER,
                WorkspaceRole.GUEST,
            )
        ),
    ],
) -> ResourceLinkResponse:
    repository = cast(WorkspaceRepository, request.app.state.workspace_repository)
    await _accessible_project(repository, project_id, user)
    exists = False
    if body.resource_type == "experiment":
        exists = (
            await cast(ExperimentRepository, request.app.state.experiment_repository).get(
                body.resource_id
            )
            is not None
        )
    elif body.resource_type == "candidate":
        exists = (
            await cast(CandidateRepository, request.app.state.candidate_repository).get(
                body.resource_id
            )
            is not None
        )
    elif body.resource_type == "report":
        exists = (
            await cast(ClosedLoopRepository, request.app.state.closed_loop_repository).get(
                body.resource_id
            )
            is not None
        )
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    resource = ProjectResource(
        project_id=project_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        linked_by=user.user_id,
    )
    try:
        await repository.link_resource(resource)
    except EvaluationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ResourceLinkResponse(
        project_id=resource.project_id,
        resource_type=resource.resource_type,
        resource_id=resource.resource_id,
        linked_by=resource.linked_by,
        linked_at=resource.linked_at,
    )
