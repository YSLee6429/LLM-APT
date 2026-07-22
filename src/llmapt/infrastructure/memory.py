"""Deterministic in-memory adapters for tests and local M1 demonstrations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from llmapt.application.ports import (
    CompilationResult,
    ExecutionResult,
    ModelRequest,
    ModelResponse,
)
from llmapt.domain.closed_loop import ClosedLoopReport
from llmapt.domain.digests import digest_bytes
from llmapt.domain.entities import ModelIdentity, RunManifest, utc_now
from llmapt.domain.enums import CandidateStatus, ExperimentStatus
from llmapt.domain.errors import EvaluationError
from llmapt.domain.experiments import ExperimentManifest, ExperimentState
from llmapt.domain.mutations import CandidateState, MutationCandidate
from llmapt.domain.oracles import OracleValidationReport
from llmapt.domain.problems import ResourceLimits
from llmapt.domain.reviews import CandidateReview
from llmapt.domain.state_machine import require_transition
from llmapt.domain.workspace import ModelProfile, Project, ProjectResource, WorkspaceUser


@dataclass(slots=True)
class DeterministicModelProvider:
    """Return exactly one configured source program without network access."""

    source: str
    identity: ModelIdentity = field(
        default_factory=lambda: ModelIdentity(
            provider="mock",
            model="deterministic-coder",
            revision="m1",
        )
    )
    requests: list[ModelRequest] = field(default_factory=list, init=False)

    async def identify(self) -> ModelIdentity:
        return self.identity

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(
            identity=self.identity,
            raw_text=self.source,
            input_tokens=len(request.prompt.split()),
            output_tokens=len(self.source.split()),
        )


@dataclass(slots=True)
class InMemoryRunRepository:
    manifests: dict[UUID, RunManifest] = field(default_factory=dict)

    async def save(self, manifest: RunManifest) -> None:
        existing = self.manifests.get(manifest.run_id)
        if existing is not None and existing != manifest:
            raise EvaluationError("run identifier collision")
        self.manifests[manifest.run_id] = manifest

    async def get(self, run_id: UUID) -> RunManifest | None:
        return self.manifests.get(run_id)


@dataclass(slots=True)
class InMemoryExperimentRepository:
    manifests: dict[UUID, ExperimentManifest] = field(default_factory=dict)
    states: dict[UUID, ExperimentState] = field(default_factory=dict)

    async def save(self, manifest: ExperimentManifest) -> None:
        existing = self.manifests.get(manifest.experiment_id)
        if existing is not None and existing != manifest:
            raise EvaluationError("experiment identifier collision")
        self.manifests[manifest.experiment_id] = manifest
        self.states.setdefault(
            manifest.experiment_id,
            ExperimentState(
                experiment_id=manifest.experiment_id,
                status=ExperimentStatus.PLANNED,
                updated_at=manifest.created_at,
            ),
        )

    async def get(self, experiment_id: UUID) -> ExperimentManifest | None:
        return self.manifests.get(experiment_id)

    async def get_state(self, experiment_id: UUID) -> ExperimentState | None:
        return self.states.get(experiment_id)

    async def list_recent(
        self, limit: int = 100
    ) -> Sequence[tuple[ExperimentManifest, ExperimentState]]:
        manifests = sorted(self.manifests.values(), key=lambda item: item.created_at, reverse=True)
        return [(item, self.states[item.experiment_id]) for item in manifests[:limit]]

    async def transition(
        self,
        experiment_id: UUID,
        expected: ExperimentStatus,
        target: ExperimentStatus,
        *,
        task_id: str | None = None,
        last_error: str | None = None,
    ) -> ExperimentState:
        state = self.states.get(experiment_id)
        if state is None:
            raise EvaluationError("experiment not found")
        if state.status is not expected:
            raise EvaluationError(
                f"experiment state conflict: expected {expected.value}, found {state.status.value}"
            )
        updated = ExperimentState(
            experiment_id=experiment_id,
            status=target,
            updated_at=utc_now(),
            task_id=task_id if task_id is not None else state.task_id,
            last_error=last_error,
        )
        self.states[experiment_id] = updated
        return updated


@dataclass(slots=True)
class InMemoryExperimentScheduler:
    tasks: list[tuple[UUID, str]] = field(default_factory=list)

    def enqueue(self, experiment_id: UUID, task_id: str) -> None:
        self.tasks.append((experiment_id, task_id))


@dataclass(slots=True)
class InMemoryCandidateRepository:
    candidates: dict[UUID, MutationCandidate] = field(default_factory=dict)
    states: dict[UUID, CandidateState] = field(default_factory=dict)

    async def save(self, candidate: MutationCandidate) -> None:
        existing = self.candidates.get(candidate.candidate_id)
        if existing is not None and existing != candidate:
            raise EvaluationError("candidate identifier collision")
        self.candidates[candidate.candidate_id] = candidate
        self.states.setdefault(
            candidate.candidate_id,
            CandidateState(
                candidate_id=candidate.candidate_id,
                status=CandidateStatus.GENERATED,
                updated_at=candidate.created_at,
            ),
        )

    async def get(self, candidate_id: UUID) -> MutationCandidate | None:
        return self.candidates.get(candidate_id)

    async def get_state(self, candidate_id: UUID) -> CandidateState | None:
        return self.states.get(candidate_id)

    async def list_recent(
        self, limit: int = 100
    ) -> Sequence[tuple[MutationCandidate, CandidateState]]:
        candidates = sorted(
            self.candidates.values(), key=lambda item: item.created_at, reverse=True
        )
        return [(item, self.states[item.candidate_id]) for item in candidates[:limit]]

    async def transition(
        self,
        candidate_id: UUID,
        expected: CandidateStatus,
        target: CandidateStatus,
        *,
        oracle_validation_id: UUID | None = None,
        reason_code: str | None = None,
    ) -> CandidateState:
        state = self.states.get(candidate_id)
        if state is None:
            raise EvaluationError("mutation candidate not found")
        if state.status is not expected:
            raise EvaluationError(
                f"candidate state conflict: expected {expected.value}, found {state.status.value}"
            )
        require_transition(expected, target)
        updated = CandidateState(
            candidate_id=candidate_id,
            status=target,
            updated_at=utc_now(),
            oracle_validation_id=(
                oracle_validation_id
                if oracle_validation_id is not None
                else state.oracle_validation_id
            ),
            reason_code=reason_code,
        )
        self.states[candidate_id] = updated
        return updated


@dataclass(slots=True)
class InMemoryOracleValidationRepository:
    reports: dict[UUID, OracleValidationReport] = field(default_factory=dict)

    async def save(self, report: OracleValidationReport) -> None:
        existing = self.reports.get(report.validation_id)
        if existing is not None and existing != report:
            raise EvaluationError("oracle validation identifier collision")
        self.reports[report.validation_id] = report

    async def get(self, validation_id: UUID) -> OracleValidationReport | None:
        return self.reports.get(validation_id)

    async def latest_for_candidate(self, candidate_id: UUID) -> OracleValidationReport | None:
        matches = [
            report for report in self.reports.values() if report.candidate_id == candidate_id
        ]
        return max(matches, key=lambda report: report.created_at, default=None)


@dataclass(slots=True)
class InMemoryCandidateReviewRepository:
    reviews: dict[UUID, CandidateReview] = field(default_factory=dict)

    async def save(self, review: CandidateReview) -> None:
        existing = self.reviews.get(review.review_id)
        if existing is not None and existing != review:
            raise EvaluationError("candidate review identifier collision")
        self.reviews[review.review_id] = review

    async def latest_for_candidate(self, candidate_id: UUID) -> CandidateReview | None:
        matches = [
            review for review in self.reviews.values() if review.candidate_id == candidate_id
        ]
        return max(matches, key=lambda review: review.created_at, default=None)


@dataclass(slots=True)
class InMemoryClosedLoopRepository:
    reports: dict[UUID, ClosedLoopReport] = field(default_factory=dict)

    async def save(self, report: ClosedLoopReport) -> None:
        existing = self.reports.get(report.report_id)
        if existing is not None and existing != report:
            raise EvaluationError("closed-loop report identifier collision")
        self.reports[report.report_id] = report

    async def get(self, report_id: UUID) -> ClosedLoopReport | None:
        return self.reports.get(report_id)

    async def list_recent(self, limit: int = 100) -> Sequence[ClosedLoopReport]:
        return sorted(self.reports.values(), key=lambda item: item.created_at, reverse=True)[:limit]


@dataclass(slots=True)
class InMemoryWorkspaceRepository:
    users: dict[UUID, WorkspaceUser] = field(default_factory=dict)
    projects: dict[UUID, Project] = field(default_factory=dict)
    profiles: dict[UUID, ModelProfile] = field(default_factory=dict)
    resources: dict[tuple[UUID, str, UUID], ProjectResource] = field(default_factory=dict)

    async def save_user(self, user: WorkspaceUser) -> None:
        if any(
            item.username.casefold() == user.username.casefold() for item in self.users.values()
        ):
            existing = next(
                item
                for item in self.users.values()
                if item.username.casefold() == user.username.casefold()
            )
            if existing != user:
                raise EvaluationError("username already exists")
            return
        self.users[user.user_id] = user

    async def update_user(self, user: WorkspaceUser) -> None:
        if user.user_id not in self.users:
            raise EvaluationError("user not found")
        self.users[user.user_id] = user

    async def get_user(self, user_id: UUID) -> WorkspaceUser | None:
        return self.users.get(user_id)

    async def get_user_by_username(self, username: str) -> WorkspaceUser | None:
        return next(
            (
                item
                for item in self.users.values()
                if item.username.casefold() == username.casefold()
            ),
            None,
        )

    async def save_project(self, project: Project) -> None:
        self.projects[project.project_id] = project

    async def get_project(self, project_id: UUID) -> Project | None:
        return self.projects.get(project_id)

    async def list_projects(self, owner_id: UUID | None = None) -> Sequence[Project]:
        projects = [
            item for item in self.projects.values() if owner_id is None or item.owner_id == owner_id
        ]
        return sorted(projects, key=lambda item: item.updated_at, reverse=True)

    async def save_model_profile(self, profile: ModelProfile) -> None:
        self.profiles[profile.profile_id] = profile

    async def list_model_profiles(self, project_id: UUID | None = None) -> Sequence[ModelProfile]:
        values = [
            item
            for item in self.profiles.values()
            if project_id is None or item.project_id == project_id
        ]
        return sorted(values, key=lambda item: item.created_at, reverse=True)

    async def link_resource(self, resource: ProjectResource) -> None:
        self.resources[(resource.project_id, resource.resource_type, resource.resource_id)] = (
            resource
        )

    async def list_resources(self, project_id: UUID) -> Sequence[ProjectResource]:
        return sorted(
            (item for item in self.resources.values() if item.project_id == project_id),
            key=lambda item: item.linked_at,
            reverse=True,
        )


@dataclass(slots=True)
class InMemoryArtifactStore:
    payloads: dict[str, bytes] = field(default_factory=dict)
    metadata: dict[str, Mapping[str, str]] = field(default_factory=dict)

    async def put(self, key: str, payload: bytes, metadata: Mapping[str, str]) -> str:
        existing = self.payloads.get(key)
        if existing is not None and existing != payload:
            raise EvaluationError(f"artifact key collision: {key}")
        self.payloads[key] = bytes(payload)
        self.metadata[key] = dict(metadata)
        return f"memory://{key}"

    async def get(self, key: str) -> bytes:
        try:
            return self.payloads[key]
        except KeyError as exc:
            raise EvaluationError(f"artifact not found: {key}") from exc


@dataclass(slots=True)
class ScriptedSandbox:
    """Implement the runner contract from predeclared facts; never execute source code."""

    executions: Mapping[bytes, ExecutionResult]
    compilation: CompilationResult | None = None
    compile_calls: list[tuple[bytes, str, ResourceLimits]] = field(default_factory=list, init=False)
    execute_calls: list[bytes] = field(default_factory=list, init=False)
    _artifact_token: str | None = field(default=None, init=False)

    async def compile(
        self,
        source: bytes,
        language: str,
        limits: ResourceLimits,
    ) -> CompilationResult:
        self.compile_calls.append((source, language, limits))
        if self.compilation is not None:
            self._artifact_token = self.compilation.artifact_token
            return self.compilation
        self._artifact_token = f"mock-compiled:{digest_bytes(source)}"
        return CompilationResult(
            succeeded=True,
            artifact_token=self._artifact_token,
            diagnostics=b"",
            duration_ms=1,
        )

    async def execute(
        self,
        artifact_token: str,
        arguments: Sequence[str],
        standard_input: bytes,
        limits: ResourceLimits,
    ) -> ExecutionResult:
        del arguments, limits
        if artifact_token != self._artifact_token:
            raise EvaluationError("unknown compiled artifact token")
        self.execute_calls.append(standard_input)
        try:
            return self.executions[standard_input]
        except KeyError as exc:
            raise EvaluationError("no scripted execution for test input") from exc
