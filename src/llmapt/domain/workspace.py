"""M3 local research workspace entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from llmapt.domain.entities import utc_now


class WorkspaceRole(StrEnum):
    ADMIN = "admin"
    GUEST = "guest"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


@dataclass(frozen=True, slots=True)
class WorkspaceUser:
    username: str
    display_name: str
    role: WorkspaceRole
    password_hash: str
    user_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    active: bool = True


@dataclass(frozen=True, slots=True)
class Project:
    name: str
    description: str
    owner_id: UUID
    project_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class ModelProfile:
    project_id: UUID
    name: str
    provider: str
    model: str
    revision: str | None
    description: str
    tags: tuple[str, ...] = ()
    profile_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class ProjectResource:
    project_id: UUID
    resource_type: str
    resource_id: UUID
    linked_by: UUID
    linked_at: datetime = field(default_factory=utc_now)
