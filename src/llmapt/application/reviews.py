"""Human admission gate after deterministic Oracle validation."""

from uuid import UUID

from llmapt.application.ports import CandidateRepository, CandidateReviewRepository
from llmapt.domain.enums import CandidateStatus, ReviewDecision
from llmapt.domain.errors import EvaluationError
from llmapt.domain.reviews import CandidateReview


class CandidateReviewService:
    def __init__(
        self,
        candidates: CandidateRepository,
        reviews: CandidateReviewRepository,
    ) -> None:
        self._candidates = candidates
        self._reviews = reviews

    async def review(
        self,
        candidate_id: UUID,
        decision: ReviewDecision,
        reviewer: str,
        justification: str,
    ) -> CandidateReview:
        state = await self._candidates.get_state(candidate_id)
        if state is None:
            raise EvaluationError("mutation candidate not found")
        if state.status is not CandidateStatus.ORACLE_VALIDATED:
            raise EvaluationError(f"candidate is not reviewable from {state.status.value}")
        review = CandidateReview(
            candidate_id=candidate_id,
            decision=decision,
            reviewer=reviewer,
            justification=justification,
        )
        await self._reviews.save(review)
        await self._candidates.transition(
            candidate_id,
            CandidateStatus.ORACLE_VALIDATED,
            CandidateStatus.READY
            if decision is ReviewDecision.APPROVE
            else CandidateStatus.REJECTED,
            reason_code=None if decision is ReviewDecision.APPROVE else "human_review_rejected",
        )
        return review
