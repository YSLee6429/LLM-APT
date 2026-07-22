"""Allowed lifecycle transitions for persistent experiment jobs."""

from llmapt.domain.enums import ExperimentStatus
from llmapt.domain.errors import InvalidTransitionError

ALLOWED_EXPERIMENT_TRANSITIONS: dict[ExperimentStatus, frozenset[ExperimentStatus]] = {
    ExperimentStatus.PLANNED: frozenset({ExperimentStatus.QUEUED, ExperimentStatus.CANCELLED}),
    ExperimentStatus.QUEUED: frozenset(
        {ExperimentStatus.RUNNING, ExperimentStatus.FAILED, ExperimentStatus.CANCELLED}
    ),
    ExperimentStatus.RUNNING: frozenset({ExperimentStatus.SUCCEEDED, ExperimentStatus.FAILED}),
    ExperimentStatus.SUCCEEDED: frozenset(),
    ExperimentStatus.FAILED: frozenset({ExperimentStatus.QUEUED}),
    ExperimentStatus.CANCELLED: frozenset(),
}


def require_experiment_transition(
    current: ExperimentStatus,
    target: ExperimentStatus,
) -> ExperimentStatus:
    if target not in ALLOWED_EXPERIMENT_TRANSITIONS[current]:
        raise InvalidTransitionError(
            f"experiment transition is not allowed: {current.value} -> {target.value}"
        )
    return target
