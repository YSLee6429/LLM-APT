"""Worker tasks for deployment verification and durable experiment preparation."""

import asyncio
from datetime import UTC, datetime
from typing import TypedDict
from uuid import UUID

from llmapt.config import get_settings
from llmapt.domain.enums import ExperimentStatus
from llmapt.domain.errors import EvaluationError
from llmapt.infrastructure.database import create_engine, create_session_factory
from llmapt.infrastructure.persistence.experiments import PostgresExperimentRepository
from llmapt.worker.celery_app import celery_app


class PingResult(TypedDict):
    status: str
    checked_at: str


class PrepareResult(TypedDict):
    experiment_id: str
    status: str
    plan_digest: str


@celery_app.task(name="llmapt.system.ping")  # type: ignore[untyped-decorator]
def ping() -> PingResult:
    """Return a JSON-safe worker heartbeat."""

    return {"status": "ok", "checked_at": datetime.now(UTC).isoformat()}


async def _prepare_experiment(experiment_id: UUID) -> PrepareResult:
    engine = create_engine(get_settings())
    repository = PostgresExperimentRepository(create_session_factory(engine))
    running = False
    try:
        state = await repository.get_state(experiment_id)
        if state is None:
            raise EvaluationError("experiment not found")
        if state.status is ExperimentStatus.SUCCEEDED:
            manifest = await repository.get(experiment_id)
            if manifest is None:
                raise EvaluationError("experiment manifest not found")
            return {
                "experiment_id": str(experiment_id),
                "status": state.status.value,
                "plan_digest": manifest.plan_digest,
            }
        if state.status is ExperimentStatus.QUEUED:
            await repository.transition(
                experiment_id,
                ExperimentStatus.QUEUED,
                ExperimentStatus.RUNNING,
            )
            running = True
        elif state.status is not ExperimentStatus.RUNNING:
            raise EvaluationError(f"experiment is not executable from {state.status.value}")
        else:
            running = True

        manifest = await repository.get(experiment_id)
        if manifest is None:
            raise EvaluationError("experiment manifest not found")
        completed = await repository.transition(
            experiment_id,
            ExperimentStatus.RUNNING,
            ExperimentStatus.SUCCEEDED,
        )
        return {
            "experiment_id": str(experiment_id),
            "status": completed.status.value,
            "plan_digest": manifest.plan_digest,
        }
    except Exception:
        if running:
            await repository.transition(
                experiment_id,
                ExperimentStatus.RUNNING,
                ExperimentStatus.FAILED,
                last_error="experiment_preparation_failed",
            )
        raise
    finally:
        await engine.dispose()


@celery_app.task(name="llmapt.experiments.prepare")  # type: ignore[untyped-decorator]
def prepare_experiment(experiment_id: str) -> PrepareResult:
    """Validate persisted experiment state before later mutation/evaluation stages."""

    return asyncio.run(_prepare_experiment(UUID(experiment_id)))
