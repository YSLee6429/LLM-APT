from uuid import uuid4

from llmapt.infrastructure.celery_scheduler import CeleryExperimentScheduler


class RecordingCelery:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str], str, str]] = []

    def send_task(
        self,
        name: str,
        args: list[str],
        task_id: str,
        queue: str,
    ) -> None:
        self.calls.append((name, args, task_id, queue))


def test_celery_scheduler_uses_explicit_task_identity_and_queue() -> None:
    celery = RecordingCelery()
    scheduler = CeleryExperimentScheduler(celery)  # type: ignore[arg-type]
    experiment_id = uuid4()

    scheduler.enqueue(experiment_id, "task-id")

    assert celery.calls == [
        ("llmapt.experiments.prepare", [str(experiment_id)], "task-id", "control")
    ]
