"""Immutable human admission decisions for Oracle-validated candidates."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from llmapt.domain.entities import utc_now
from llmapt.domain.enums import ReviewDecision


@dataclass(frozen=True, slots=True)
class CandidateReview:
    candidate_id: UUID
    decision: ReviewDecision
    reviewer: str
    justification: str
    review_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.reviewer.strip() or len(self.reviewer) > 128:
            raise ValueError("reviewer must contain 1 to 128 characters")
        if not self.justification.strip() or len(self.justification) > 2000:
            raise ValueError("justification must contain 1 to 2000 characters")
