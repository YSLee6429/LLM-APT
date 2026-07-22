from dataclasses import replace

import pytest

from llmapt.application.mutations import MutationService
from llmapt.application.oracle_registry import OracleRegistry, RegisteredOracle
from llmapt.application.oracle_validation import OracleValidationService
from llmapt.domain.digests import digest_text
from llmapt.domain.entities import utc_now
from llmapt.domain.enums import (
    CandidateStatus,
    MutationKind,
    OracleValidationVerdict,
    OutputPolicy,
)
from llmapt.domain.errors import EvaluationError
from llmapt.domain.mutations import CandidateState
from llmapt.domain.oracles import OracleIdentity
from llmapt.domain.problems import ProblemSpec, ResourceLimits
from llmapt.domain.problems import TestCase as DomainTestCase
from llmapt.infrastructure.memory import (
    InMemoryCandidateRepository,
    InMemoryOracleValidationRepository,
)


def _parent(*, wrong_expected: bool = False) -> ProblemSpec:
    return ProblemSpec(
        problem_id="double",
        title="Double an Integer",
        statement="Read one integer n and print 2 * n.",
        language="cpp",
        output_policy=OutputPolicy.TRIM_TRAILING_WHITESPACE,
        limits=ResourceLimits(time_limit_ms=1000, memory_limit_mb=128),
        tests=(
            DomainTestCase("positive", b"2\n", b"5\n" if wrong_expected else b"4\n"),
            DomainTestCase("negative", b"-3\n", b"-6\n"),
        ),
    )


def _oracle(*, evaluator=None) -> RegisteredOracle:  # type: ignore[no-untyped-def]
    return RegisteredOracle(
        identity=OracleIdentity(
            key="test.double",
            version="1",
            parent_problem_id="double",
            parent_statement_digest=digest_text("Read one integer n and print 2 * n."),
            language="cpp",
        ),
        evaluate=evaluator or (lambda data: f"{int(data) * 2}\n".encode()),
    )


@pytest.mark.asyncio
async def test_registered_oracle_admits_matching_candidate_idempotently() -> None:
    candidate = MutationService().mutate(_parent(), MutationKind.TEST_ORDER_ROTATION, random_seed=7)
    candidates = InMemoryCandidateRepository()
    validations = InMemoryOracleValidationRepository()
    await candidates.save(candidate)
    service = OracleValidationService(
        candidates,
        validations,
        OracleRegistry((_oracle(),)),
    )

    first = await service.validate(candidate.candidate_id, "test.double")
    second = await service.validate(candidate.candidate_id, "test.double")
    state = await candidates.get_state(candidate.candidate_id)

    assert first == second
    assert first.verdict is OracleValidationVerdict.PASSED
    assert first.passed_cases == 2
    assert state is not None
    assert state.status is CandidateStatus.ORACLE_VALIDATED
    assert state.oracle_validation_id == first.validation_id


@pytest.mark.asyncio
async def test_oracle_rejects_incorrect_expected_output() -> None:
    candidate = MutationService().mutate(
        _parent(wrong_expected=True), MutationKind.TEST_ORDER_ROTATION, random_seed=3
    )
    candidates = InMemoryCandidateRepository()
    validations = InMemoryOracleValidationRepository()
    await candidates.save(candidate)

    report = await OracleValidationService(
        candidates, validations, OracleRegistry((_oracle(),))
    ).validate(candidate.candidate_id, "test.double")
    state = await candidates.get_state(candidate.candidate_id)

    assert report.verdict is OracleValidationVerdict.REJECTED
    assert report.reason_code == "oracle_output_mismatch"
    assert any(not case.matched for case in report.cases)
    assert state is not None and state.status is CandidateStatus.REJECTED


@pytest.mark.asyncio
async def test_oracle_binding_mismatch_rejects_spoofed_parent() -> None:
    parent = replace(_parent(), statement="Different problem semantics.")
    candidate = MutationService().mutate(parent, MutationKind.TEST_ORDER_ROTATION, random_seed=1)
    candidates = InMemoryCandidateRepository()
    validations = InMemoryOracleValidationRepository()
    await candidates.save(candidate)

    report = await OracleValidationService(
        candidates, validations, OracleRegistry((_oracle(),))
    ).validate(candidate.candidate_id, "test.double")

    assert report.verdict is OracleValidationVerdict.REJECTED
    assert report.reason_code == "oracle_statement_binding_mismatch"
    assert report.cases == ()


@pytest.mark.asyncio
async def test_unexpected_oracle_failure_quarantines_candidate() -> None:
    def broken(_data: bytes) -> bytes:
        raise RuntimeError("secret implementation detail")

    candidate = MutationService().mutate(_parent(), MutationKind.TEST_ORDER_ROTATION, random_seed=5)
    candidates = InMemoryCandidateRepository()
    validations = InMemoryOracleValidationRepository()
    await candidates.save(candidate)

    report = await OracleValidationService(
        candidates,
        validations,
        OracleRegistry((_oracle(evaluator=broken),)),
    ).validate(candidate.candidate_id, "test.double")
    state = await candidates.get_state(candidate.candidate_id)

    assert report.verdict is OracleValidationVerdict.ERROR
    assert report.reason_code == "oracle_execution_failed"
    assert "secret" not in report.reason_code
    assert state is not None and state.status is CandidateStatus.QUARANTINED


def test_registry_rejects_duplicates_and_unknown_keys() -> None:
    oracle = _oracle()
    with pytest.raises(ValueError, match="duplicate oracle"):
        OracleRegistry((oracle, oracle))
    with pytest.raises(EvaluationError, match="not found"):
        OracleRegistry().resolve("missing")


@pytest.mark.asyncio
async def test_missing_candidate_and_corrupt_idempotency_record_are_rejected() -> None:
    candidates = InMemoryCandidateRepository()
    validations = InMemoryOracleValidationRepository()
    service = OracleValidationService(candidates, validations, OracleRegistry((_oracle(),)))
    candidate = MutationService().mutate(_parent(), MutationKind.TEST_ORDER_ROTATION, random_seed=2)

    with pytest.raises(EvaluationError, match="candidate not found"):
        await service.validate(candidate.candidate_id, "test.double")

    await candidates.save(candidate)
    candidates.states[candidate.candidate_id] = CandidateState(
        candidate_id=candidate.candidate_id,
        status=CandidateStatus.ORACLE_VALIDATED,
        updated_at=utc_now(),
    )
    with pytest.raises(EvaluationError, match="record not found"):
        await service.validate(candidate.candidate_id, "test.double")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("identity_change", "expected_reason"),
    [
        ({"parent_problem_id": "other"}, "oracle_problem_binding_mismatch"),
        ({"language": "python"}, "oracle_language_binding_mismatch"),
    ],
)
async def test_oracle_identity_binding_is_enforced(
    identity_change: dict[str, str],
    expected_reason: str,
) -> None:
    candidate = MutationService().mutate(_parent(), MutationKind.TEST_ORDER_ROTATION, random_seed=4)
    candidates = InMemoryCandidateRepository()
    validations = InMemoryOracleValidationRepository()
    await candidates.save(candidate)
    base = _oracle()
    changed = RegisteredOracle(
        identity=replace(base.identity, **identity_change),
        evaluate=base.evaluate,
    )

    report = await OracleValidationService(
        candidates, validations, OracleRegistry((changed,))
    ).validate(candidate.candidate_id, "test.double")

    assert report.reason_code == expected_reason


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("evaluator", "max_input_bytes", "output_limit", "expected_reason"),
    [
        (lambda _data: b"4\n", 1, 1024, "oracle_input_too_large"),
        (lambda _data: b"123456", 1024, 1, "oracle_output_too_large"),
        (
            lambda _data: (_ for _ in ()).throw(ValueError("bad integer")),
            1024,
            1024,
            "oracle_input_rejected",
        ),
    ],
)
async def test_oracle_resource_and_input_rejections_are_sanitized(
    evaluator,  # type: ignore[no-untyped-def]
    max_input_bytes: int,
    output_limit: int,
    expected_reason: str,
) -> None:
    parent = replace(
        _parent(),
        limits=replace(_parent().limits, output_limit_bytes=output_limit),
    )
    candidate = MutationService().mutate(parent, MutationKind.TEST_ORDER_ROTATION, random_seed=6)
    candidates = InMemoryCandidateRepository()
    validations = InMemoryOracleValidationRepository()
    await candidates.save(candidate)

    report = await OracleValidationService(
        candidates,
        validations,
        OracleRegistry((_oracle(evaluator=evaluator),)),
        max_input_bytes=max_input_bytes,
    ).validate(candidate.candidate_id, "test.double")

    assert report.verdict is OracleValidationVerdict.REJECTED
    assert report.reason_code == expected_reason
