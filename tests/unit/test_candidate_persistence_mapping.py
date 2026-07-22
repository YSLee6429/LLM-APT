from llmapt.application.mutations import MutationService
from llmapt.domain.enums import CandidateStatus, MutationKind, OracleValidationVerdict
from llmapt.domain.oracles import OracleCaseValidation, OracleIdentity, OracleValidationReport
from llmapt.domain.problems import ProblemSpec, ResourceLimits
from llmapt.domain.problems import TestCase as DomainTestCase
from llmapt.infrastructure.persistence.candidates import (
    _candidate_to_domain,
    _candidate_to_state,
    _oracle_report_to_domain,
    _problem_to_json,
)
from llmapt.infrastructure.persistence.models import (
    MutationCandidateRecord,
    OracleValidationRecord,
)


def _candidate():  # type: ignore[no-untyped-def]
    problem = ProblemSpec(
        problem_id="binary",
        title="Binary bytes",
        statement="Echo a byte sequence.",
        language="cpp",
        tests=(DomainTestCase("binary", b"\x00\xff", b"\xff\x00"),),
        limits=ResourceLimits(time_limit_ms=1, memory_limit_mb=1),
    )
    return MutationService().mutate(
        problem,
        MutationKind.BOUNDARY_CLAUSE,
        random_seed=9,
        boundary_clause="Binary input is permitted.",
    )


def test_candidate_record_round_trip_preserves_binary_cases() -> None:
    candidate = _candidate()
    record = MutationCandidateRecord(
        candidate_id=candidate.candidate_id,
        created_at=candidate.created_at,
        operator=candidate.operator.value,
        parent_problem_id=candidate.parent_problem_id,
        parent_statement_digest=candidate.parent_statement_digest,
        parent_test_suite_digest=candidate.parent_test_suite_digest,
        random_seed=candidate.random_seed,
        notes=list(candidate.notes),
        problem_data=_problem_to_json(candidate.problem),
        status=CandidateStatus.GENERATED.value,
        updated_at=candidate.created_at,
        oracle_validation_id=None,
        reason_code=None,
    )

    assert _candidate_to_domain(record) == candidate
    assert _candidate_to_state(record).status is CandidateStatus.GENERATED


def test_oracle_validation_record_round_trip() -> None:
    candidate = _candidate()
    identity = OracleIdentity(
        key="binary.v1",
        version="1",
        parent_problem_id="binary",
        parent_statement_digest=candidate.parent_statement_digest,
        language="cpp",
    )
    case = OracleCaseValidation(
        case_id="binary",
        input_digest="a" * 64,
        expected_output_digest="b" * 64,
        actual_output_digest="b" * 64,
        matched=True,
    )
    report = OracleValidationReport(
        candidate_id=candidate.candidate_id,
        oracle=identity,
        candidate_statement_digest=candidate.problem.statement_digest,
        candidate_test_suite_digest=candidate.problem.test_suite_digest,
        verdict=OracleValidationVerdict.PASSED,
        cases=(case,),
    )
    record = OracleValidationRecord(
        validation_id=report.validation_id,
        candidate_id=report.candidate_id,
        created_at=report.created_at,
        oracle_key=identity.key,
        oracle_version=identity.version,
        parent_problem_id=identity.parent_problem_id,
        parent_statement_digest=identity.parent_statement_digest,
        language=identity.language,
        candidate_statement_digest=report.candidate_statement_digest,
        candidate_test_suite_digest=report.candidate_test_suite_digest,
        verdict=report.verdict.value,
        cases=[
            {
                "case_id": case.case_id,
                "input_digest": case.input_digest,
                "expected_output_digest": case.expected_output_digest,
                "actual_output_digest": case.actual_output_digest,
                "matched": case.matched,
                "reason_code": "reviewed",
            }
        ],
        reason_code="reviewed",
    )

    restored = _oracle_report_to_domain(record)
    assert restored.reason_code == "reviewed"
    assert restored.cases[0].reason_code == "reviewed"
