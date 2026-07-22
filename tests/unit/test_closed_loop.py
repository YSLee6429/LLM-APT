import pytest

from llmapt.application.closed_loop import ClosedLoopRequest, ClosedLoopService
from llmapt.application.mutations import MutationService
from llmapt.application.oracle_validation import OracleValidationService
from llmapt.application.ports import CompilationResult, ExecutionResult
from llmapt.application.provider_registry import ProviderRegistry
from llmapt.application.reviews import CandidateReviewService
from llmapt.domain.entities import ModelIdentity
from llmapt.domain.enums import EvidenceLevel, MutationKind, ReviewDecision, Verdict
from llmapt.domain.problems import ProblemSpec, ResourceLimits
from llmapt.domain.problems import TestCase as DomainTestCase
from llmapt.infrastructure.memory import (
    DeterministicModelProvider,
    InMemoryCandidateRepository,
    InMemoryCandidateReviewRepository,
    InMemoryClosedLoopRepository,
    InMemoryOracleValidationRepository,
    ScriptedSandbox,
)
from llmapt.infrastructure.oracles import build_oracle_registry


def _problem() -> ProblemSpec:
    return ProblemSpec(
        problem_id="double",
        title="Double",
        statement="Read one integer n and print 2 * n.",
        language="cpp",
        tests=(
            DomainTestCase("positive", b"2\n", b"4\n"),
            DomainTestCase("negative", b"-3\n", b"-6\n"),
        ),
        limits=ResourceLimits(1000, 128),
    )


async def _ready_candidate():  # type: ignore[no-untyped-def]
    candidate = MutationService().mutate(
        _problem(), MutationKind.TEST_ORDER_ROTATION, random_seed=1
    )
    candidates = InMemoryCandidateRepository()
    validations = InMemoryOracleValidationRepository()
    await candidates.save(candidate)
    await OracleValidationService(candidates, validations, build_oracle_registry()).validate(
        candidate.candidate_id, "builtin.double"
    )
    await CandidateReviewService(candidates, InMemoryCandidateReviewRepository()).review(
        candidate.candidate_id,
        ReviewDecision.APPROVE,
        "reviewer",
        "review complete",
    )
    return candidate, candidates, validations


def _providers() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(
        "local",
        DeterministicModelProvider(
            source="#include <iostream>\nint main(){std::cout<<0<<'\\n';}",
            identity=ModelIdentity("local", "wrong-coder", "test"),
        ),
        external=False,
    )
    return registry


@pytest.mark.asyncio
async def test_closed_loop_upgrades_repeated_wa_and_reduces_input() -> None:
    candidate, candidates, validations = await _ready_candidate()
    reports = InMemoryClosedLoopRepository()
    sandbox = ScriptedSandbox(
        executions={
            b"-3\n": ExecutionResult(0, b"0\n", b"", 1),
            b"-3": ExecutionResult(0, b"0\n", b"", 1),
        }
    )
    service = ClosedLoopService(
        candidates,
        validations,
        reports,
        _providers(),
        build_oracle_registry(),
        sandbox,
    )

    report = await service.run(
        ClosedLoopRequest(
            candidate.candidate_id,
            "builtin.double",
            "local",
            "Solve the problem.",
            2,
            {"temperature": 0},
        )
    )

    assert report.verdict is Verdict.WRONG_ANSWER
    assert report.evidence_level is EvidenceLevel.REPRODUCIBLE_FAILURE
    assert report.stable_failure is True
    assert report.counterexample is not None
    assert report.counterexample.minimized_input == b"-3"
    assert report.counterexample.minimized_size < report.counterexample.original_size
    assert await reports.get(report.report_id) == report


@pytest.mark.asyncio
async def test_closed_loop_repeated_compile_error_is_reproducible() -> None:
    candidate, candidates, validations = await _ready_candidate()
    sandbox = ScriptedSandbox(
        executions={},
        compilation=CompilationResult(False, None, b"error", 1),
    )
    report = await ClosedLoopService(
        candidates,
        validations,
        InMemoryClosedLoopRepository(),
        _providers(),
        build_oracle_registry(),
        sandbox,
    ).run(ClosedLoopRequest(candidate.candidate_id, "builtin.double", "local", "Solve.", 2, {}))

    assert report.verdict is Verdict.COMPILE_ERROR
    assert report.evidence_level is EvidenceLevel.REPRODUCIBLE_FAILURE
    assert report.counterexample is None
