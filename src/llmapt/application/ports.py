"""Typed boundaries implemented by external adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from llmapt.domain.closed_loop import ClosedLoopReport
from llmapt.domain.entities import ModelIdentity, RunManifest
from llmapt.domain.enums import CandidateStatus, ExperimentStatus
from llmapt.domain.experiments import ExperimentManifest, ExperimentState
from llmapt.domain.mutations import CandidateState, MutationCandidate
from llmapt.domain.oracles import OracleValidationReport
from llmapt.domain.problems import ResourceLimits
from llmapt.domain.reviews import CandidateReview
from llmapt.domain.workspace import ModelProfile, Project, ProjectResource, WorkspaceUser


@dataclass(frozen=True, slots=True)
class ModelRequest:
    prompt: str
    language: str
    parameters: Mapping[str, str | int | float | bool]


@dataclass(frozen=True, slots=True)
class ModelResponse:
    identity: ModelIdentity
    raw_text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class CompilationResult:
    succeeded: bool
    artifact_token: str | None
    diagnostics: bytes
    duration_ms: int


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    duration_ms: int
    timed_out: bool = False
    memory_exceeded: bool = False
    output_exceeded: bool = False
    infrastructure_error: bool = False


class ModelProvider(Protocol):
    async def identify(self) -> ModelIdentity: ...

    async def generate(self, request: ModelRequest) -> ModelResponse: ...


class RunRepository(Protocol):
    async def save(self, manifest: RunManifest) -> None: ...

    async def get(self, run_id: UUID) -> RunManifest | None: ...


class ExperimentRepository(Protocol):
    async def save(self, manifest: ExperimentManifest) -> None: ...

    async def get(self, experiment_id: UUID) -> ExperimentManifest | None: ...

    async def get_state(self, experiment_id: UUID) -> ExperimentState | None: ...

    async def list_recent(
        self, limit: int = 100
    ) -> Sequence[tuple[ExperimentManifest, ExperimentState]]: ...

    async def transition(
        self,
        experiment_id: UUID,
        expected: ExperimentStatus,
        target: ExperimentStatus,
        *,
        task_id: str | None = None,
        last_error: str | None = None,
    ) -> ExperimentState: ...


class ExperimentScheduler(Protocol):
    def enqueue(self, experiment_id: UUID, task_id: str) -> None: ...


class CandidateRepository(Protocol):
    async def save(self, candidate: MutationCandidate) -> None: ...

    async def get(self, candidate_id: UUID) -> MutationCandidate | None: ...

    async def get_state(self, candidate_id: UUID) -> CandidateState | None: ...

    async def list_recent(
        self, limit: int = 100
    ) -> Sequence[tuple[MutationCandidate, CandidateState]]: ...

    async def transition(
        self,
        candidate_id: UUID,
        expected: CandidateStatus,
        target: CandidateStatus,
        *,
        oracle_validation_id: UUID | None = None,
        reason_code: str | None = None,
    ) -> CandidateState: ...


class OracleValidationRepository(Protocol):
    async def save(self, report: OracleValidationReport) -> None: ...

    async def get(self, validation_id: UUID) -> OracleValidationReport | None: ...

    async def latest_for_candidate(self, candidate_id: UUID) -> OracleValidationReport | None: ...


class CandidateReviewRepository(Protocol):
    async def save(self, review: CandidateReview) -> None: ...

    async def latest_for_candidate(self, candidate_id: UUID) -> CandidateReview | None: ...


class ClosedLoopRepository(Protocol):
    async def save(self, report: ClosedLoopReport) -> None: ...

    async def get(self, report_id: UUID) -> ClosedLoopReport | None: ...

    async def list_recent(self, limit: int = 100) -> Sequence[ClosedLoopReport]: ...


class WorkspaceRepository(Protocol):
    async def save_user(self, user: WorkspaceUser) -> None: ...

    async def update_user(self, user: WorkspaceUser) -> None: ...

    async def get_user(self, user_id: UUID) -> WorkspaceUser | None: ...

    async def get_user_by_username(self, username: str) -> WorkspaceUser | None: ...

    async def save_project(self, project: Project) -> None: ...

    async def get_project(self, project_id: UUID) -> Project | None: ...

    async def list_projects(self, owner_id: UUID | None = None) -> Sequence[Project]: ...

    async def save_model_profile(self, profile: ModelProfile) -> None: ...

    async def list_model_profiles(
        self, project_id: UUID | None = None
    ) -> Sequence[ModelProfile]: ...

    async def link_resource(self, resource: ProjectResource) -> None: ...

    async def list_resources(self, project_id: UUID) -> Sequence[ProjectResource]: ...


class ArtifactStore(Protocol):
    async def put(self, key: str, payload: bytes, metadata: Mapping[str, str]) -> str: ...

    async def get(self, key: str) -> bytes: ...


class Sandbox(Protocol):
    async def compile(
        self,
        source: bytes,
        language: str,
        limits: ResourceLimits,
    ) -> CompilationResult: ...

    async def execute(
        self,
        artifact_token: str,
        arguments: Sequence[str],
        standard_input: bytes,
        limits: ResourceLimits,
    ) -> ExecutionResult: ...
