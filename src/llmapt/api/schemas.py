"""Public API response models."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from llmapt.demo import MockScenario
from llmapt.domain.enums import (
    CandidateStatus,
    EvidenceLevel,
    ExperimentStatus,
    MutationKind,
    OracleValidationVerdict,
    OutputPolicy,
    ReviewDecision,
    Verdict,
)
from llmapt.domain.experiments import ParameterValue
from llmapt.domain.problems import ProblemSpec, ResourceLimits, TestCase


class ServiceInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    environment: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    service: str
    version: str
    checked_at: datetime


class ReadinessResponse(HealthResponse):
    components: dict[str, str]


class MockEvaluationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario: MockScenario = MockScenario.ACCEPTED
    random_seed: int = 7


class CaseEvaluationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    verdict: Verdict
    duration_ms: int
    input_digest: str
    expected_output_digest: str
    actual_output_digest: str


class MockEvaluationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    problem_id: str
    verdict: Verdict
    evidence_level: EvidenceLevel
    passed_cases: int
    total_cases: int
    cases: tuple[CaseEvaluationResponse, ...]
    ephemeral_artifacts: bool = True


class ResourceLimitsDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    time_limit_ms: int = Field(ge=1)
    memory_limit_mb: int = Field(ge=1)
    process_limit: int = Field(default=1, ge=1)
    output_limit_bytes: int = Field(default=1_048_576, ge=1)


class TestCaseDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1, max_length=128)
    standard_input: str
    expected_output: str
    hidden: bool = True


class ProblemDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    problem_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=256)
    statement: str = Field(min_length=1)
    language: str = Field(min_length=1, max_length=32)
    tests: tuple[TestCaseDefinition, ...] = Field(min_length=1)
    limits: ResourceLimitsDefinition
    output_policy: OutputPolicy = OutputPolicy.TRIM_TRAILING_WHITESPACE

    def to_domain(self) -> ProblemSpec:
        return ProblemSpec(
            problem_id=self.problem_id,
            title=self.title,
            statement=self.statement,
            language=self.language,
            tests=tuple(
                TestCase(
                    case_id=test.case_id,
                    standard_input=test.standard_input.encode("utf-8"),
                    expected_output=test.expected_output.encode("utf-8"),
                    hidden=test.hidden,
                )
                for test in self.tests
            ),
            limits=ResourceLimits(**self.limits.model_dump()),
            output_policy=self.output_policy,
        )

    @classmethod
    def from_domain(cls, problem: ProblemSpec) -> Self:
        return cls(
            problem_id=problem.problem_id,
            title=problem.title,
            statement=problem.statement,
            language=problem.language,
            tests=tuple(
                TestCaseDefinition(
                    case_id=test.case_id,
                    standard_input=test.standard_input.decode("utf-8"),
                    expected_output=test.expected_output.decode("utf-8"),
                    hidden=test.hidden,
                )
                for test in problem.tests
            ),
            limits=ResourceLimitsDefinition(
                time_limit_ms=problem.limits.time_limit_ms,
                memory_limit_mb=problem.limits.memory_limit_mb,
                process_limit=problem.limits.process_limit,
                output_limit_bytes=problem.limits.output_limit_bytes,
            ),
            output_policy=problem.output_policy,
        )


class ProblemValidationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid: bool = True
    problem_id: str
    test_count: int
    statement_digest: str
    test_suite_digest: str


class ModelIdentityResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    model: str
    revision: str | None


class ProviderResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    identity: ModelIdentityResponse
    external: bool


class GenerationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_key: str = Field(default="local", min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=200_000)
    language: str = Field(min_length=1, max_length=32)
    parameters: dict[str, ParameterValue] = Field(default_factory=dict)


class GenerationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    identity: ModelIdentityResponse
    source: str
    raw_response_digest: str
    source_digest: str
    extracted_from_fence: bool
    input_tokens: int | None
    output_tokens: int | None


class ExperimentPlanRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    problem: ProblemDefinition
    provider_key: str = Field(default="local", min_length=1, max_length=64)
    prompt_template_version: str = Field(default="m2-v1", min_length=1, max_length=128)
    random_seed: int = 7
    repetitions: int = Field(default=1, ge=1, le=100)
    parameters: dict[str, ParameterValue] = Field(default_factory=dict)


class ExperimentPlanResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    experiment_id: UUID
    created_at: datetime
    problem_id: str
    statement_digest: str
    test_suite_digest: str
    target: ModelIdentityResponse
    prompt_template_version: str
    random_seed: int
    repetitions: int
    parameters: dict[str, ParameterValue]
    plan_digest: str
    ephemeral_storage: bool = True


class ExperimentStateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    experiment_id: UUID
    status: ExperimentStatus
    updated_at: datetime
    task_id: str | None
    last_error: str | None


class ExperimentDispatchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    experiment_id: UUID
    task_id: str
    status: ExperimentStatus


class MutationPreviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    problem: ProblemDefinition
    operator: MutationKind
    random_seed: int = 7
    boundary_clause: str | None = Field(default=None, max_length=2_000)


class MutationPreviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: UUID
    created_at: datetime
    operator: MutationKind
    parent_problem_id: str
    parent_statement_digest: str
    parent_test_suite_digest: str
    random_seed: int
    notes: tuple[str, ...]
    requires_oracle_validation: bool
    problem: ProblemDefinition


class CandidateStateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: UUID
    status: CandidateStatus
    updated_at: datetime
    oracle_validation_id: UUID | None
    reason_code: str | None


class OracleIdentityResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    version: str
    parent_problem_id: str
    parent_statement_digest: str
    language: str


class OracleValidationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: UUID
    oracle_key: str = Field(min_length=1, max_length=128)


class OracleCaseValidationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    input_digest: str
    expected_output_digest: str
    actual_output_digest: str
    matched: bool
    reason_code: str | None


class OracleValidationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    validation_id: UUID
    candidate_id: UUID
    created_at: datetime
    oracle: OracleIdentityResponse
    candidate_statement_digest: str
    candidate_test_suite_digest: str
    verdict: OracleValidationVerdict
    cases: tuple[OracleCaseValidationResponse, ...]
    passed_cases: int
    total_cases: int
    reason_code: str | None


class CandidateReviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: ReviewDecision
    reviewer: str = Field(min_length=1, max_length=128)
    justification: str = Field(min_length=1, max_length=2_000)


class CandidateReviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    review_id: UUID
    candidate_id: UUID
    created_at: datetime
    decision: ReviewDecision
    reviewer: str
    justification: str
    candidate_status: CandidateStatus


class ClosedLoopRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: UUID
    oracle_key: str = Field(min_length=1, max_length=128)
    provider_key: str = Field(default="local", min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=200_000)
    repetitions: int = Field(default=2, ge=2, le=10)
    parameters: dict[str, ParameterValue] = Field(default_factory=dict)


class RepetitionObservationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    repetition: int
    source_digest: str
    raw_response_digest: str
    verdict: Verdict
    failure_case_id: str | None
    input_digest: str | None
    expected_output_digest: str | None
    actual_output_digest: str | None


class CounterexampleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    original_input_digest: str
    minimized_input_digest: str
    expected_output_digest: str
    actual_output_digest: str
    original_size: int
    minimized_size: int
    attempts: int


class ClosedLoopReportResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: UUID
    candidate_id: UUID
    oracle_validation_id: UUID
    created_at: datetime
    target: ModelIdentityResponse
    repetitions_requested: int
    repetitions_completed: int
    verdict: Verdict
    evidence_level: EvidenceLevel
    stable_failure: bool
    observations: tuple[RepetitionObservationResponse, ...]
    counterexample: CounterexampleResponse | None
