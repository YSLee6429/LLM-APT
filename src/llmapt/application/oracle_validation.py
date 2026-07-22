"""Validate mutation outputs with a server-registered trusted oracle."""

from __future__ import annotations

from uuid import UUID

from llmapt.application.judge import outputs_match
from llmapt.application.oracle_registry import OracleRegistry, RegisteredOracle
from llmapt.application.ports import CandidateRepository, OracleValidationRepository
from llmapt.domain.digests import digest_bytes
from llmapt.domain.enums import CandidateStatus, OracleValidationVerdict
from llmapt.domain.errors import EvaluationError
from llmapt.domain.mutations import MutationCandidate
from llmapt.domain.oracles import OracleCaseValidation, OracleValidationReport


class OracleValidationService:
    def __init__(
        self,
        candidates: CandidateRepository,
        validations: OracleValidationRepository,
        registry: OracleRegistry,
        *,
        max_input_bytes: int = 1_048_576,
    ) -> None:
        self._candidates = candidates
        self._validations = validations
        self._registry = registry
        self._max_input_bytes = max_input_bytes

    async def validate(self, candidate_id: UUID, oracle_key: str) -> OracleValidationReport:
        candidate = await self._candidates.get(candidate_id)
        state = await self._candidates.get_state(candidate_id)
        if candidate is None or state is None:
            raise EvaluationError("mutation candidate not found")
        if state.status is CandidateStatus.ORACLE_VALIDATED:
            existing = await self._validations.latest_for_candidate(candidate_id)
            if existing is None:
                raise EvaluationError("oracle validation record not found")
            return existing
        if state.status is CandidateStatus.GENERATED:
            state = await self._candidates.transition(
                candidate_id,
                CandidateStatus.GENERATED,
                CandidateStatus.STRUCTURE_VALIDATED,
            )
        if state.status is not CandidateStatus.STRUCTURE_VALIDATED:
            raise EvaluationError(f"candidate is not oracle-validatable from {state.status.value}")

        oracle = self._registry.resolve(oracle_key)
        binding_error = self._binding_error(candidate, oracle)
        if binding_error is not None:
            return await self._record_terminal(
                candidate,
                oracle,
                OracleValidationVerdict.REJECTED,
                (),
                binding_error,
                CandidateStatus.REJECTED,
            )

        cases: list[OracleCaseValidation] = []
        try:
            for test_case in candidate.problem.tests:
                if len(test_case.standard_input) > self._max_input_bytes:
                    raise ValueError("oracle_input_too_large")
                actual = oracle.evaluate(test_case.standard_input)
                if len(actual) > candidate.problem.limits.output_limit_bytes:
                    raise ValueError("oracle_output_too_large")
                matched = outputs_match(
                    test_case.expected_output,
                    actual,
                    candidate.problem.output_policy,
                )
                cases.append(
                    OracleCaseValidation(
                        case_id=test_case.case_id,
                        input_digest=test_case.input_digest,
                        expected_output_digest=test_case.expected_output_digest,
                        actual_output_digest=digest_bytes(actual),
                        matched=matched,
                        reason_code=None if matched else "oracle_output_mismatch",
                    )
                )
        except ValueError as exc:
            reason_code = str(exc) if str(exc).startswith("oracle_") else "oracle_input_rejected"
            return await self._record_terminal(
                candidate,
                oracle,
                OracleValidationVerdict.REJECTED,
                tuple(cases),
                reason_code,
                CandidateStatus.REJECTED,
            )
        except Exception:
            return await self._record_terminal(
                candidate,
                oracle,
                OracleValidationVerdict.ERROR,
                tuple(cases),
                "oracle_execution_failed",
                CandidateStatus.QUARANTINED,
            )

        passed = all(case.matched for case in cases)
        return await self._record_terminal(
            candidate,
            oracle,
            OracleValidationVerdict.PASSED if passed else OracleValidationVerdict.REJECTED,
            tuple(cases),
            None if passed else "oracle_output_mismatch",
            CandidateStatus.ORACLE_VALIDATED if passed else CandidateStatus.REJECTED,
        )

    @staticmethod
    def _binding_error(candidate: MutationCandidate, oracle: RegisteredOracle) -> str | None:
        identity = oracle.identity
        if candidate.parent_problem_id != identity.parent_problem_id:
            return "oracle_problem_binding_mismatch"
        if candidate.parent_statement_digest != identity.parent_statement_digest:
            return "oracle_statement_binding_mismatch"
        if candidate.problem.language != identity.language:
            return "oracle_language_binding_mismatch"
        return None

    async def _record_terminal(
        self,
        candidate: MutationCandidate,
        oracle: RegisteredOracle,
        verdict: OracleValidationVerdict,
        cases: tuple[OracleCaseValidation, ...],
        reason_code: str | None,
        target: CandidateStatus,
    ) -> OracleValidationReport:
        report = OracleValidationReport(
            candidate_id=candidate.candidate_id,
            oracle=oracle.identity,
            candidate_statement_digest=candidate.problem.statement_digest,
            candidate_test_suite_digest=candidate.problem.test_suite_digest,
            verdict=verdict,
            cases=cases,
            reason_code=reason_code,
        )
        await self._validations.save(report)
        await self._candidates.transition(
            candidate.candidate_id,
            CandidateStatus.STRUCTURE_VALIDATED,
            target,
            oracle_validation_id=report.validation_id,
            reason_code=reason_code,
        )
        return report
