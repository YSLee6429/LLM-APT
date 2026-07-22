"""Recoverable experiment dispatch orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from llmapt.application.ports import ExperimentRepository, ExperimentScheduler
from llmapt.domain.enums import ExperimentStatus
from llmapt.domain.errors import EvaluationError
from llmapt.domain.experiment_state_machine import require_experiment_transition
from llmapt.domain.experiments import ExperimentState


@dataclass(frozen=True, slots=True)
class DispatchReceipt:
    experiment_id: UUID
    task_id: str
    state: ExperimentState


class ExperimentDispatchService:
    def __init__(
        self,
        experiments: ExperimentRepository,
        scheduler: ExperimentScheduler,
    ) -> None:
        self._experiments = experiments
        self._scheduler = scheduler

    async def enqueue(self, experiment_id: UUID) -> DispatchReceipt:
        manifest = await self._experiments.get(experiment_id)
        state = await self._experiments.get_state(experiment_id)
        if manifest is None or state is None:
            raise EvaluationError("experiment not found")
        require_experiment_transition(state.status, ExperimentStatus.QUEUED)

        task_id = str(uuid4())
        queued = await self._experiments.transition(
            experiment_id,
            state.status,
            ExperimentStatus.QUEUED,
            task_id=task_id,
        )
        try:
            self._scheduler.enqueue(experiment_id, task_id)
        except Exception as exc:
            await self._experiments.transition(
                experiment_id,
                ExperimentStatus.QUEUED,
                ExperimentStatus.FAILED,
                last_error="scheduler_publish_failed",
            )
            raise EvaluationError("experiment could not be queued") from exc
        return DispatchReceipt(experiment_id=experiment_id, task_id=task_id, state=queued)
