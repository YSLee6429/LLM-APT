"""PostgreSQL persistence for the M3 local research workspace."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from llmapt.domain.errors import EvaluationError
from llmapt.domain.workspace import (
    ModelProfile,
    Project,
    ProjectResource,
    WorkspaceRole,
    WorkspaceUser,
)
from llmapt.infrastructure.persistence.models import (
    ModelProfileRecord,
    ProjectRecord,
    ProjectResourceRecord,
    WorkspaceUserRecord,
)


class PostgresWorkspaceRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save_user(self, user: WorkspaceUser) -> None:
        try:
            async with self._sessions.begin() as session:
                existing = await session.get(WorkspaceUserRecord, user.user_id)
                if existing is not None:
                    return
                session.add(
                    WorkspaceUserRecord(
                        user_id=user.user_id,
                        username=user.username,
                        display_name=user.display_name,
                        role=user.role.value,
                        password_hash=user.password_hash,
                        created_at=user.created_at,
                        active=user.active,
                    )
                )
        except IntegrityError as exc:
            raise EvaluationError("username already exists") from exc

    async def update_user(self, user: WorkspaceUser) -> None:
        async with self._sessions.begin() as session:
            record = await session.get(WorkspaceUserRecord, user.user_id)
            if record is None:
                raise EvaluationError("user not found")
            record.display_name = user.display_name
            record.role = user.role.value
            record.password_hash = user.password_hash
            record.active = user.active

    async def get_user(self, user_id: UUID) -> WorkspaceUser | None:
        async with self._sessions() as session:
            record = await session.get(WorkspaceUserRecord, user_id)
            return None if record is None else _user(record)

    async def get_user_by_username(self, username: str) -> WorkspaceUser | None:
        async with self._sessions() as session:
            record = (
                await session.execute(
                    select(WorkspaceUserRecord).where(
                        WorkspaceUserRecord.username == username.casefold()
                    )
                )
            ).scalar_one_or_none()
            return None if record is None else _user(record)

    async def save_project(self, project: Project) -> None:
        async with self._sessions.begin() as session:
            session.add(
                ProjectRecord(
                    project_id=project.project_id,
                    name=project.name,
                    description=project.description,
                    owner_id=project.owner_id,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                )
            )

    async def get_project(self, project_id: UUID) -> Project | None:
        async with self._sessions() as session:
            record = await session.get(ProjectRecord, project_id)
            return None if record is None else _project(record)

    async def list_projects(self, owner_id: UUID | None = None) -> list[Project]:
        statement = select(ProjectRecord).order_by(ProjectRecord.updated_at.desc())
        if owner_id is not None:
            statement = statement.where(ProjectRecord.owner_id == owner_id)
        async with self._sessions() as session:
            records = (await session.execute(statement)).scalars()
            return [_project(record) for record in records]

    async def save_model_profile(self, profile: ModelProfile) -> None:
        async with self._sessions.begin() as session:
            session.add(
                ModelProfileRecord(
                    profile_id=profile.profile_id,
                    project_id=profile.project_id,
                    name=profile.name,
                    provider=profile.provider,
                    model=profile.model,
                    revision=profile.revision,
                    description=profile.description,
                    tags=list(profile.tags),
                    created_at=profile.created_at,
                )
            )

    async def list_model_profiles(self, project_id: UUID | None = None) -> list[ModelProfile]:
        statement = select(ModelProfileRecord).order_by(ModelProfileRecord.created_at.desc())
        if project_id is not None:
            statement = statement.where(ModelProfileRecord.project_id == project_id)
        async with self._sessions() as session:
            records = (await session.execute(statement)).scalars()
            return [_profile(record) for record in records]

    async def link_resource(self, resource: ProjectResource) -> None:
        try:
            async with self._sessions.begin() as session:
                session.add(
                    ProjectResourceRecord(
                        link_id=uuid4(),
                        project_id=resource.project_id,
                        resource_type=resource.resource_type,
                        resource_id=resource.resource_id,
                        linked_by=resource.linked_by,
                        linked_at=resource.linked_at,
                    )
                )
        except IntegrityError as exc:
            raise EvaluationError("resource is already linked or project is invalid") from exc

    async def list_resources(self, project_id: UUID) -> list[ProjectResource]:
        async with self._sessions() as session:
            records = (
                await session.execute(
                    select(ProjectResourceRecord)
                    .where(ProjectResourceRecord.project_id == project_id)
                    .order_by(ProjectResourceRecord.linked_at.desc())
                )
            ).scalars()
            return [
                ProjectResource(
                    project_id=record.project_id,
                    resource_type=record.resource_type,
                    resource_id=record.resource_id,
                    linked_by=record.linked_by,
                    linked_at=record.linked_at,
                )
                for record in records
            ]


def _user(record: WorkspaceUserRecord) -> WorkspaceUser:
    return WorkspaceUser(
        user_id=record.user_id,
        username=record.username,
        display_name=record.display_name,
        role=WorkspaceRole(record.role),
        password_hash=record.password_hash,
        created_at=record.created_at,
        active=record.active,
    )


def _project(record: ProjectRecord) -> Project:
    return Project(
        project_id=record.project_id,
        name=record.name,
        description=record.description,
        owner_id=record.owner_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _profile(record: ModelProfileRecord) -> ModelProfile:
    return ModelProfile(
        profile_id=record.profile_id,
        project_id=record.project_id,
        name=record.name,
        provider=record.provider,
        model=record.model,
        revision=record.revision,
        description=record.description,
        tags=tuple(record.tags),
        created_at=record.created_at,
    )
