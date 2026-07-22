from uuid import uuid4

from llmapt.domain.entities import utc_now
from llmapt.domain.enums import ExperimentStatus
from llmapt.infrastructure.persistence.experiments import PostgresExperimentRepository
from llmapt.infrastructure.persistence.models import ExperimentRecord


def test_experiment_record_round_trips_to_domain_objects() -> None:
    experiment_id = uuid4()
    created_at = utc_now()
    record = ExperimentRecord(
        experiment_id=experiment_id,
        created_at=created_at,
        problem_id="problem",
        statement_digest="a" * 64,
        test_suite_digest="b" * 64,
        provider="provider",
        model="model",
        revision="revision",
        prompt_template_version="v1",
        random_seed=7,
        repetitions=2,
        parameters={"max_tokens": 1024, "temperature": 0},
        plan_digest="c" * 64,
        status=ExperimentStatus.QUEUED.value,
        updated_at=created_at,
        task_id="task-id",
        last_error=None,
    )

    manifest = PostgresExperimentRepository._to_domain(record)
    state = PostgresExperimentRepository._to_state(record)

    assert manifest.experiment_id == experiment_id
    assert manifest.parameters == (("max_tokens", 1024), ("temperature", 0))
    assert state.status is ExperimentStatus.QUEUED
    assert state.task_id == "task-id"
