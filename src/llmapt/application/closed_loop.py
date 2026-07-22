"""Complete generation, isolated execution, reproduction, and reduction loop."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

from llmapt.application.judge import classify_execution
from llmapt.application.oracle_registry import OracleRegistry
from llmapt.application.ports import (
    CandidateRepository,
    ClosedLoopRepository,
    ModelRequest,
    OracleValidationRepository,
    Sandbox,
)
from llmapt.application.provider_registry import ProviderRegistry
from llmapt.application.reducer import TokenDeltaReducer
from llmapt.application.source_extraction import extract_candidate_source
from llmapt.domain.closed_loop import (
    ClosedLoopReport,
    Counterexample,
    RepetitionObservation,
)
from llmapt.domain.digests import digest_bytes, digest_text
from llmapt.domain.enums import CandidateStatus, EvidenceLevel, OracleValidationVerdict, Verdict
from llmapt.domain.errors import EvaluationError
from llmapt.domain.mutations import MutationCandidate

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ClosedLoopRequest:
    candidate_id: UUID
    oracle_key: str
    provider_key: str
    prompt: str
    repetitions: int
    parameters: Mapping[str, str | int | float | bool]


class ClosedLoopService:
    def __init__(
        self,
        candidates: CandidateRepository,
        validations: OracleValidationRepository,
        reports: ClosedLoopRepository,
        providers: ProviderRegistry,
        oracles: OracleRegistry,
        sandbox: Sandbox,
    ) -> None:
        self._candidates = candidates
        self._validations = validations
        self._reports = reports
        self._providers = providers
        self._oracles = oracles
        self._sandbox = sandbox

    async def run(self, request: ClosedLoopRequest) -> ClosedLoopReport:
        if not 2 <= request.repetitions <= 10:
            raise EvaluationError("closed-loop repetitions must be between 2 and 10")
        candidate = await self._candidates.get(request.candidate_id)
        state = await self._candidates.get_state(request.candidate_id)
        if candidate is None or state is None:
            raise EvaluationError("mutation candidate not found")
        if state.status is not CandidateStatus.READY or state.oracle_validation_id is None:
            raise EvaluationError("candidate is not ready for evaluation")
        validation = await self._validations.get(state.oracle_validation_id)
        if validation is None or validation.verdict is not OracleValidationVerdict.PASSED:
            raise EvaluationError("candidate has no passing Oracle validation")
        oracle = self._oracles.resolve(request.oracle_key)
        if oracle.identity != validation.oracle:
            raise EvaluationError("Oracle identity does not match candidate validation")
        provider = self._providers.get(request.provider_key)
        identity = await provider.identify()
        await self._candidates.transition(
            candidate.candidate_id,
            CandidateStatus.READY,
            CandidateStatus.EVALUATING,
        )

        observations: list[RepetitionObservation] = []
        reduction_context: tuple[str, str, RepetitionObservation] | None = None
        for repetition in range(1, request.repetitions + 1):
            response = await self._guard(
                candidate.candidate_id,
                provider.generate(
                    ModelRequest(request.prompt, candidate.problem.language, request.parameters)
                ),
            )
            if response.identity != identity:
                await self._candidates.transition(
                    candidate.candidate_id,
                    CandidateStatus.EVALUATING,
                    CandidateStatus.RETRY_WAIT,
                    reason_code="model_identity_changed",
                )
                raise EvaluationError("model identity changed during closed-loop evaluation")
            extracted = extract_candidate_source(response.raw_text, candidate.problem.language)
            source = extracted.source.encode()
            source_digest = digest_bytes(source)
            compilation = await self._guard(
                candidate.candidate_id,
                self._sandbox.compile(source, candidate.problem.language, candidate.problem.limits),
            )
            if not compilation.succeeded or compilation.artifact_token is None:
                observations.append(
                    RepetitionObservation(
                        repetition=repetition,
                        source_digest=source_digest,
                        raw_response_digest=digest_text(response.raw_text),
                        source_text=extracted.source,
                        raw_response_text=response.raw_text,
                        verdict=Verdict.COMPILE_ERROR,
                    )
                )
                continue

            observation = await self._guard(
                candidate.candidate_id,
                self._execute_tests(
                    repetition,
                    candidate,
                    compilation.artifact_token,
                    source_digest,
                    extracted.source,
                    response.raw_text,
                ),
            )
            observations.append(observation)
            if reduction_context is None and observation.verdict is Verdict.WRONG_ANSWER:
                reduction_context = (
                    observation.failure_case_id or "unknown",
                    compilation.artifact_token,
                    observation,
                )

        verdict, evidence_level, stable = self._aggregate(observations)
        counterexample = None
        if stable and verdict is Verdict.WRONG_ANSWER and reduction_context is not None:
            case_id, artifact_token, observation_object = reduction_context
            observation = observation_object
            test_case = next(case for case in candidate.problem.tests if case.case_id == case_id)
            counterexample = await self._guard(
                candidate.candidate_id,
                self._reduce(
                    candidate,
                    oracle.evaluate,
                    artifact_token,
                    test_case.standard_input,
                    case_id,
                ),
            )

        report = ClosedLoopReport(
            candidate_id=candidate.candidate_id,
            oracle_validation_id=validation.validation_id,
            target=identity,
            repetitions_requested=request.repetitions,
            repetitions_completed=len(observations),
            verdict=verdict,
            evidence_level=evidence_level,
            stable_failure=stable,
            observations=tuple(observations),
            counterexample=counterexample,
        )
        await self._guard(candidate.candidate_id, self._reports.save(report))
        await self._candidates.transition(
            candidate.candidate_id,
            CandidateStatus.EVALUATING,
            CandidateStatus.EVALUATED,
        )
        return report

    async def _guard(self, candidate_id: UUID, operation: Awaitable[T]) -> T:
        try:
            return await operation
        except Exception:
            await self._candidates.transition(
                candidate_id,
                CandidateStatus.EVALUATING,
                CandidateStatus.RETRY_WAIT,
                reason_code="closed_loop_execution_failed",
            )
            raise

    async def _execute_tests(
        self,
        repetition: int,
        candidate: MutationCandidate,
        artifact_token: str,
        source_digest: str,
        source_text: str,
        raw_response_text: str,
    ) -> RepetitionObservation:
        for case in candidate.problem.tests:
            execution = await self._sandbox.execute(
                artifact_token, (), case.standard_input, candidate.problem.limits
            )
            verdict = classify_execution(
                execution, case.expected_output, candidate.problem.output_policy
            )
            if verdict is not Verdict.ACCEPTED:
                return RepetitionObservation(
                    repetition=repetition,
                    source_digest=source_digest,
                    raw_response_digest=digest_text(raw_response_text),
                    source_text=source_text,
                    raw_response_text=raw_response_text,
                    verdict=verdict,
                    failure_case_id=case.case_id,
                    input_digest=case.input_digest,
                    expected_output_digest=case.expected_output_digest,
                    actual_output_digest=digest_bytes(execution.stdout),
                    actual_output=execution.stdout,
                )
        return RepetitionObservation(
            repetition=repetition,
            source_digest=source_digest,
            raw_response_digest=digest_text(raw_response_text),
            source_text=source_text,
            raw_response_text=raw_response_text,
            verdict=Verdict.ACCEPTED,
        )

    @staticmethod
    def _aggregate(
        observations: list[RepetitionObservation],
    ) -> tuple[Verdict, EvidenceLevel, bool]:
        if any(item.verdict is Verdict.INFRASTRUCTURE_ERROR for item in observations):
            return Verdict.INCONCLUSIVE, EvidenceLevel.NONE, False
        signatures = {
            (
                item.verdict,
                item.source_digest,
                item.failure_case_id,
                item.actual_output_digest,
            )
            for item in observations
        }
        if len(signatures) == 1:
            verdict = observations[0].verdict
            if verdict is Verdict.ACCEPTED:
                return verdict, EvidenceLevel.NONE, False
            return verdict, EvidenceLevel.REPRODUCIBLE_FAILURE, True
        return Verdict.INCONCLUSIVE, EvidenceLevel.OBSERVED_DIFFERENCE, False

    async def _reduce(
        self,
        candidate: MutationCandidate,
        oracle_evaluate: Callable[[bytes], bytes],
        artifact_token: str,
        original: bytes,
        case_id: str,
    ) -> Counterexample:
        latest_expected = b""
        latest_actual = b""

        async def predicate(value: bytes) -> bool:
            nonlocal latest_expected, latest_actual
            try:
                expected = oracle_evaluate(value)
            except (ValueError, UnicodeError):
                return False
            execution = await self._sandbox.execute(
                artifact_token, (), value, candidate.problem.limits
            )
            if execution.infrastructure_error:
                return False
            verdict = classify_execution(execution, expected, candidate.problem.output_policy)
            if verdict is Verdict.WRONG_ANSWER:
                latest_expected = expected
                latest_actual = execution.stdout
                return True
            return False

        reduced = await TokenDeltaReducer().reduce(original, predicate)
        if not latest_expected:
            latest_expected = oracle_evaluate(reduced.minimized_input)
            execution = await self._sandbox.execute(
                artifact_token, (), reduced.minimized_input, candidate.problem.limits
            )
            latest_actual = execution.stdout
        return Counterexample(
            case_id=case_id,
            original_input_digest=digest_bytes(original),
            minimized_input_digest=digest_bytes(reduced.minimized_input),
            minimized_input=reduced.minimized_input,
            expected_output_digest=digest_bytes(latest_expected),
            actual_output_digest=digest_bytes(latest_actual),
            original_size=len(original),
            minimized_size=len(reduced.minimized_input),
            attempts=reduced.attempts,
        )
