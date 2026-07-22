import pytest

from llmapt.domain.enums import ExperimentStatus
from llmapt.domain.errors import InvalidTransitionError
from llmapt.domain.experiment_state_machine import require_experiment_transition


def test_experiment_happy_path_is_allowed() -> None:
    assert (
        require_experiment_transition(ExperimentStatus.PLANNED, ExperimentStatus.QUEUED)
        is ExperimentStatus.QUEUED
    )
    assert (
        require_experiment_transition(ExperimentStatus.QUEUED, ExperimentStatus.RUNNING)
        is ExperimentStatus.RUNNING
    )
    assert (
        require_experiment_transition(ExperimentStatus.RUNNING, ExperimentStatus.SUCCEEDED)
        is ExperimentStatus.SUCCEEDED
    )


def test_terminal_experiment_cannot_be_reopened() -> None:
    with pytest.raises(InvalidTransitionError, match="succeeded -> queued"):
        require_experiment_transition(ExperimentStatus.SUCCEEDED, ExperimentStatus.QUEUED)
