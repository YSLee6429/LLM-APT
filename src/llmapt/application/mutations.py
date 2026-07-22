"""Deterministic, explicitly registered problem mutation operators."""

from __future__ import annotations

from dataclasses import replace

from llmapt.domain.enums import MutationKind, OutputPolicy
from llmapt.domain.errors import EvaluationError
from llmapt.domain.mutations import MutationCandidate
from llmapt.domain.problems import ProblemSpec


class MutationService:
    def mutate(
        self,
        problem: ProblemSpec,
        kind: MutationKind,
        *,
        random_seed: int,
        boundary_clause: str | None = None,
    ) -> MutationCandidate:
        if kind is MutationKind.TEST_ORDER_ROTATION:
            return self._rotate_tests(problem, random_seed)
        if kind is MutationKind.BOUNDARY_CLAUSE:
            return self._append_boundary_clause(problem, random_seed, boundary_clause)
        if kind is MutationKind.OUTPUT_POLICY_EXACT:
            return self._tighten_output_policy(problem, random_seed)
        raise AssertionError(f"unhandled mutation kind: {kind}")

    @staticmethod
    def _rotate_tests(problem: ProblemSpec, random_seed: int) -> MutationCandidate:
        if len(problem.tests) < 2:
            raise EvaluationError("test-order mutation requires at least two test cases")
        offset = abs(random_seed) % (len(problem.tests) - 1) + 1
        rotated = problem.tests[offset:] + problem.tests[:offset]
        mutated = replace(
            problem,
            problem_id=f"{problem.problem_id}--order-{random_seed}",
            tests=rotated,
        )
        return _candidate(
            problem,
            mutated,
            MutationKind.TEST_ORDER_ROTATION,
            random_seed,
            (f"rotated {len(problem.tests)} tests by {offset}",),
        )

    @staticmethod
    def _append_boundary_clause(
        problem: ProblemSpec,
        random_seed: int,
        boundary_clause: str | None,
    ) -> MutationCandidate:
        clause = (boundary_clause or "").strip()
        if not clause:
            raise EvaluationError("boundary-clause mutation requires a non-blank clause")
        if len(clause) > 2_000:
            raise EvaluationError("boundary clause exceeds 2000 characters")
        mutated = replace(
            problem,
            problem_id=f"{problem.problem_id}--boundary-{random_seed}",
            statement=f"{problem.statement.rstrip()}\n\nBoundary condition:\n{clause}",
        )
        return _candidate(
            problem,
            mutated,
            MutationKind.BOUNDARY_CLAUSE,
            random_seed,
            ("statement changed; trusted oracle review is mandatory",),
        )

    @staticmethod
    def _tighten_output_policy(problem: ProblemSpec, random_seed: int) -> MutationCandidate:
        if problem.output_policy is OutputPolicy.EXACT:
            raise EvaluationError("output policy is already exact")
        mutated = replace(
            problem,
            problem_id=f"{problem.problem_id}--exact-{random_seed}",
            output_policy=OutputPolicy.EXACT,
        )
        return _candidate(
            problem,
            mutated,
            MutationKind.OUTPUT_POLICY_EXACT,
            random_seed,
            ("output comparison tightened to exact bytes",),
        )


def _candidate(
    parent: ProblemSpec,
    mutated: ProblemSpec,
    kind: MutationKind,
    random_seed: int,
    notes: tuple[str, ...],
) -> MutationCandidate:
    return MutationCandidate(
        operator=kind,
        parent_problem_id=parent.problem_id,
        parent_statement_digest=parent.statement_digest,
        parent_test_suite_digest=parent.test_suite_digest,
        problem=mutated,
        random_seed=random_seed,
        notes=notes,
    )
