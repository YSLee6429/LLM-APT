from uuid import uuid4

import pytest

from llmapt.application.mutations import MutationService
from llmapt.application.oracle_validation import OracleValidationService
from llmapt.application.reviews import CandidateReviewService
from llmapt.domain.enums import CandidateStatus, MutationKind, ReviewDecision
from llmapt.domain.errors import EvaluationError
from llmapt.domain.problems import ProblemSpec, ResourceLimits
from llmapt.domain.problems import TestCase as DomainTestCase
from llmapt.domain.reviews import CandidateReview
from llmapt.infrastructure.memory import (
    InMemoryCandidateRepository,
    InMemoryCandidateReviewRepository,
    InMemoryOracleValidationRepository,
)
from llmapt.infrastructure.oracles import build_oracle_registry


def _parent() -> ProblemSpec:
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


@pytest.mark.asyncio
async def test_human_approval_moves_oracle_validated_candidate_to_ready() -> None:
    candidate = MutationService().mutate(_parent(), MutationKind.TEST_ORDER_ROTATION, random_seed=1)
    candidates = InMemoryCandidateRepository()
    validations = InMemoryOracleValidationRepository()
    reviews = InMemoryCandidateReviewRepository()
    await candidates.save(candidate)
    validation = await OracleValidationService(
        candidates, validations, build_oracle_registry()
    ).validate(candidate.candidate_id, "builtin.double")

    review = await CandidateReviewService(candidates, reviews).review(
        candidate.candidate_id,
        ReviewDecision.APPROVE,
        "reviewer@example.test",
        "Oracle binding and mutation semantics reviewed.",
    )
    state = await candidates.get_state(candidate.candidate_id)

    assert review == await reviews.latest_for_candidate(candidate.candidate_id)
    assert state is not None and state.status is CandidateStatus.READY
    assert state.oracle_validation_id == validation.validation_id


@pytest.mark.asyncio
async def test_review_rejects_missing_or_unvalidated_candidate() -> None:
    candidate = MutationService().mutate(_parent(), MutationKind.TEST_ORDER_ROTATION, random_seed=1)
    candidates = InMemoryCandidateRepository()
    service = CandidateReviewService(candidates, InMemoryCandidateReviewRepository())
    with pytest.raises(EvaluationError, match="not found"):
        await service.review(candidate.candidate_id, ReviewDecision.REJECT, "r", "reason")
    await candidates.save(candidate)
    with pytest.raises(EvaluationError, match="not reviewable"):
        await service.review(candidate.candidate_id, ReviewDecision.REJECT, "r", "reason")


def test_review_audit_fields_cannot_be_blank() -> None:
    with pytest.raises(ValueError, match="reviewer"):
        CandidateReview(uuid4(), ReviewDecision.APPROVE, " ", "checked")
    with pytest.raises(ValueError, match="justification"):
        CandidateReview(uuid4(), ReviewDecision.APPROVE, "reviewer", " ")
