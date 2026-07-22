"""Immutable mutation proposals that cannot bypass oracle validation."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from llmapt.domain.entities import utc_now
from llmapt.domain.enums import CandidateStatus, MutationKind
from llmapt.domain.problems import ProblemSpec


@dataclass(frozen=True, slots=True)
class MutationCandidate:
    operator: MutationKind
    parent_problem_id: str
    parent_statement_digest: str
    parent_test_suite_digest: str
    problem: ProblemSpec
    random_seed: int
    notes: tuple[str, ...]
    requires_oracle_validation: bool = True
    candidate_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.requires_oracle_validation:
            raise ValueError("mutation candidates must require oracle validation")
        if self.problem.problem_id == self.parent_problem_id:
            raise ValueError("mutated problem_id must differ from its parent")


@dataclass(frozen=True, slots=True)
class CandidateState:
    candidate_id: UUID
    status: CandidateStatus
    updated_at: datetime
    oracle_validation_id: UUID | None = None
    reason_code: str | None = None
