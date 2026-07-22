from uuid import uuid4

import pytest

from llmapt.application.dispatch import ExperimentDispatchService
from llmapt.domain.entities import ModelIdentity
from llmapt.domain.enums import ExperimentStatus
from llmapt.domain.errors import EvaluationError, InvalidTransitionError
from llmapt.domain.experiments import ExperimentManifest
from llmapt.infrastructure.memory import (
    InMemoryExperimentRepository,
    InMemoryExperimentScheduler,
)


def _manifest() -> ExperimentManifest:
    return ExperimentManifest(
        problem_id="problem",
        statement_digest="a" * 64,
        test_suite_digest="b" * 64,
        target=ModelIdentity("local", "coder", "m2"),
        prompt_template_version="v1",
        random_seed=7,
        repetitions=1,
    )


@pytest.mark.asyncio
async def test_dispatch_persists_task_id_before_scheduling() -> None:
    repository = InMemoryExperimentRepository()
    scheduler = InMemoryExperimentScheduler()
    manifest = _manifest()
    await repository.save(manifest)

    receipt = await ExperimentDispatchService(repository, scheduler).enqueue(manifest.experiment_id)

    assert receipt.state.status is ExperimentStatus.QUEUED
    assert scheduler.tasks == [(manifest.experiment_id, receipt.task_id)]
    assert (await repository.get_state(manifest.experiment_id)) == receipt.state


@pytest.mark.asyncio
async def test_dispatch_rejects_missing_and_duplicate_jobs() -> None:
    repository = InMemoryExperimentRepository()
    scheduler = InMemoryExperimentScheduler()
    service = ExperimentDispatchService(repository, scheduler)

    with pytest.raises(EvaluationError, match="not found"):
        await service.enqueue(uuid4())

    manifest = _manifest()
    await repository.save(manifest)
    await service.enqueue(manifest.experiment_id)
    with pytest.raises(InvalidTransitionError, match="queued -> queued"):
        await service.enqueue(manifest.experiment_id)


class FailingScheduler:
    def enqueue(self, experiment_id: object, task_id: str) -> None:
        del experiment_id, task_id
        raise RuntimeError("broker detail must not escape")


@pytest.mark.asyncio
async def test_scheduler_failure_becomes_retryable_failed_state() -> None:
    repository = InMemoryExperimentRepository()
    manifest = _manifest()
    await repository.save(manifest)

    with pytest.raises(EvaluationError, match="could not be queued"):
        await ExperimentDispatchService(repository, FailingScheduler()).enqueue(
            manifest.experiment_id
        )

    state = await repository.get_state(manifest.experiment_id)
    assert state is not None
    assert state.status is ExperimentStatus.FAILED
    assert state.last_error == "scheduler_publish_failed"
