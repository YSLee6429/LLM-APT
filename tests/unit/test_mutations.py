import pytest

from llmapt.application.mutations import MutationService
from llmapt.domain.enums import MutationKind, OutputPolicy
from llmapt.domain.errors import EvaluationError
from llmapt.domain.mutations import MutationCandidate
from llmapt.domain.problems import ProblemSpec, ResourceLimits
from llmapt.domain.problems import TestCase as ProblemTestCase


def _problem() -> ProblemSpec:
    return ProblemSpec(
        problem_id="runs",
        title="Runs",
        statement="Count equal runs.",
        language="cpp",
        tests=(
            ProblemTestCase("first", b"1\n", b"1\n"),
            ProblemTestCase("last", b"3\n1 1 1\n", b"1\n"),
            ProblemTestCase("mixed", b"3\n1 2 2\n", b"2\n"),
        ),
        limits=ResourceLimits(1000, 128),
    )


def test_test_order_rotation_is_deterministic_and_changes_digest() -> None:
    service = MutationService()
    first = service.mutate(_problem(), MutationKind.TEST_ORDER_ROTATION, random_seed=7)
    second = service.mutate(_problem(), MutationKind.TEST_ORDER_ROTATION, random_seed=7)

    assert [case.case_id for case in first.problem.tests] == ["mixed", "first", "last"]
    assert first.problem.test_suite_digest == second.problem.test_suite_digest
    assert first.problem.test_suite_digest != first.parent_test_suite_digest
    assert first.requires_oracle_validation is True


def test_boundary_clause_is_explicitly_unvalidated() -> None:
    candidate = MutationService().mutate(
        _problem(),
        MutationKind.BOUNDARY_CLAUSE,
        random_seed=3,
        boundary_clause="The final run must also be counted.",
    )

    assert "final run" in candidate.problem.statement
    assert "trusted oracle review is mandatory" in candidate.notes[0]
    assert candidate.problem.tests == _problem().tests


def test_exact_output_policy_mutation_and_invalid_inputs() -> None:
    service = MutationService()
    candidate = service.mutate(_problem(), MutationKind.OUTPUT_POLICY_EXACT, random_seed=1)
    assert candidate.problem.output_policy is OutputPolicy.EXACT

    with pytest.raises(EvaluationError, match="already exact"):
        service.mutate(candidate.problem, MutationKind.OUTPUT_POLICY_EXACT, random_seed=1)
    with pytest.raises(EvaluationError, match="non-blank"):
        service.mutate(_problem(), MutationKind.BOUNDARY_CLAUSE, random_seed=1)
    with pytest.raises(EvaluationError, match="at least two"):
        service.mutate(
            ProblemSpec(
                "single",
                "Single",
                "Statement",
                "cpp",
                (ProblemTestCase("only", b"", b""),),
                ResourceLimits(1000, 128),
            ),
            MutationKind.TEST_ORDER_ROTATION,
            random_seed=1,
        )
    with pytest.raises(EvaluationError, match="2000 characters"):
        service.mutate(
            _problem(),
            MutationKind.BOUNDARY_CLAUSE,
            random_seed=1,
            boundary_clause="x" * 2001,
        )


def test_mutation_candidate_cannot_bypass_oracle_gate_or_reuse_parent_id() -> None:
    problem = _problem()
    values = {
        "operator": MutationKind.TEST_ORDER_ROTATION,
        "parent_problem_id": problem.problem_id,
        "parent_statement_digest": problem.statement_digest,
        "parent_test_suite_digest": problem.test_suite_digest,
        "problem": problem,
        "random_seed": 1,
        "notes": (),
    }
    with pytest.raises(ValueError, match="must require oracle"):
        MutationCandidate(**values, requires_oracle_validation=False)
    with pytest.raises(ValueError, match="must differ"):
        MutationCandidate(**values)
