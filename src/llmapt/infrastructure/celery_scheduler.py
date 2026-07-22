"""Celery implementation of the experiment scheduling port."""

from uuid import UUID

from celery import Celery

from llmapt.config import Settings


class CeleryExperimentScheduler:
    def __init__(self, celery: Celery) -> None:
        self._celery = celery

    def enqueue(self, experiment_id: UUID, task_id: str) -> None:
        self._celery.send_task(
            "llmapt.experiments.prepare",
            args=[str(experiment_id)],
            task_id=task_id,
            queue="control",
        )


def build_scheduler(settings: Settings) -> CeleryExperimentScheduler:
    celery = Celery("llmapt-api-producer", broker=settings.broker_url, backend=settings.redis_url)
    return CeleryExperimentScheduler(celery)
