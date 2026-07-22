"""Candidate evaluation state machine."""

from __future__ import annotations

from llmapt.domain.enums import CandidateStatus
from llmapt.domain.errors import InvalidTransitionError

ALLOWED_TRANSITIONS: dict[CandidateStatus, frozenset[CandidateStatus]] = {
    CandidateStatus.GENERATED: frozenset(
        {CandidateStatus.STRUCTURE_VALIDATED, CandidateStatus.REJECTED}
    ),
    CandidateStatus.STRUCTURE_VALIDATED: frozenset(
        {
            CandidateStatus.ORACLE_VALIDATED,
            CandidateStatus.REJECTED,
            CandidateStatus.QUARANTINED,
        }
    ),
    CandidateStatus.ORACLE_VALIDATED: frozenset(
        {CandidateStatus.READY, CandidateStatus.QUARANTINED}
    ),
    CandidateStatus.READY: frozenset({CandidateStatus.EVALUATING}),
    CandidateStatus.EVALUATING: frozenset({CandidateStatus.EVALUATED, CandidateStatus.RETRY_WAIT}),
    CandidateStatus.EVALUATED: frozenset({CandidateStatus.ANALYZED}),
    CandidateStatus.ANALYZED: frozenset(),
    CandidateStatus.RETRY_WAIT: frozenset({CandidateStatus.EVALUATING, CandidateStatus.REJECTED}),
    CandidateStatus.REJECTED: frozenset(),
    CandidateStatus.QUARANTINED: frozenset({CandidateStatus.READY, CandidateStatus.REJECTED}),
}


def can_transition(current: CandidateStatus, target: CandidateStatus) -> bool:
    """Return whether the requested transition is permitted."""

    return target in ALLOWED_TRANSITIONS[current]


def require_transition(current: CandidateStatus, target: CandidateStatus) -> CandidateStatus:
    """Validate and return the target state for functional composition."""

    if not can_transition(current, target):
        message = f"candidate transition is not allowed: {current.value} -> {target.value}"
        raise InvalidTransitionError(message)
    return target
