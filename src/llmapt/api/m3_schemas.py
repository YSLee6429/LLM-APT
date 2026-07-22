"""Public schemas for the M3 evaluation workspace."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from llmapt.domain.enums import CandidateStatus, EvidenceLevel, ExperimentStatus, Verdict
from llmapt.domain.workspace import WorkspaceRole


class LoginRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class UserResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_id: UUID
    username: str
    display_name: str
    role: WorkspaceRole


class LoginResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4_000)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    project_id: UUID
    name: str
    description: str
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    resource_count: int = 0
    model_profile_count: int = 0


class ModelProfileCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str = Field(min_length=1, max_length=160)
    provider: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=256)
    revision: str | None = Field(default=None, max_length=256)
    description: str = Field(default="", max_length=4_000)
    tags: tuple[str, ...] = Field(default=(), max_length=32)


class ModelProfileResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    profile_id: UUID
    project_id: UUID
    name: str
    provider: str
    model: str
    revision: str | None
    description: str
    tags: tuple[str, ...]
    created_at: datetime


class ResourceLinkRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    resource_type: str = Field(pattern="^(experiment|candidate|report)$")
    resource_id: UUID


class ResourceLinkResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    project_id: UUID
    resource_type: str
    resource_id: UUID
    linked_by: UUID
    linked_at: datetime


class ExperimentSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    experiment_id: UUID
    created_at: datetime
    problem_id: str
    provider: str
    model: str
    status: ExperimentStatus
    repetitions: int
    plan_digest: str


class CandidateSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidate_id: UUID
    created_at: datetime
    parent_problem_id: str
    operator: str
    status: CandidateStatus
    oracle_validation_id: UUID | None


class EvidenceSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    report_id: UUID
    candidate_id: UUID
    created_at: datetime
    provider: str
    model: str
    verdict: Verdict
    evidence_level: EvidenceLevel
    stable_failure: bool
    repetitions_completed: int
    has_counterexample: bool


class DashboardResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    projects: int
    model_profiles: int
    experiments: int
    candidates: int
    evidence_reports: int
    stable_failures: int
    verdict_counts: dict[str, int]
    experiment_status_counts: dict[str, int]
    candidate_status_counts: dict[str, int]
    recent_experiments: tuple[ExperimentSummaryResponse, ...]
    recent_evidence: tuple[EvidenceSummaryResponse, ...]
