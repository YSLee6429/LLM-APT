from itertools import pairwise

import pytest

from llmapt.domain.enums import CandidateStatus
from llmapt.domain.errors import InvalidTransitionError
from llmapt.domain.state_machine import can_transition, require_transition


def test_happy_path_transitions_are_allowed() -> None:
    path = [
        CandidateStatus.GENERATED,
        CandidateStatus.STRUCTURE_VALIDATED,
        CandidateStatus.ORACLE_VALIDATED,
        CandidateStatus.READY,
        CandidateStatus.EVALUATING,
        CandidateStatus.EVALUATED,
        CandidateStatus.ANALYZED,
    ]

    assert all(can_transition(current, target) for current, target in pairwise(path))


def test_agent_cannot_skip_validation_gates() -> None:
    with pytest.raises(InvalidTransitionError, match="not allowed"):
        require_transition(CandidateStatus.GENERATED, CandidateStatus.EVALUATING)


def test_terminal_state_cannot_be_reopened() -> None:
    assert not can_transition(CandidateStatus.ANALYZED, CandidateStatus.EVALUATING)
