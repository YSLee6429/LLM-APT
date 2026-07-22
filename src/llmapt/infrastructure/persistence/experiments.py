"""PostgreSQL-backed experiment repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from llmapt.domain.entities import ModelIdentity, utc_now
from llmapt.domain.enums import ExperimentStatus
from llmapt.domain.errors import EvaluationError
from llmapt.domain.experiments import ExperimentManifest, ExperimentState
from llmapt.infrastructure.persistence.models import ExperimentRecord


class PostgresExperimentRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, manifest: ExperimentManifest) -> None:
        record = ExperimentRecord(
            experiment_id=manifest.experiment_id,
            created_at=manifest.created_at,
            problem_id=manifest.problem_id,
            statement_digest=manifest.statement_digest,
            test_suite_digest=manifest.test_suite_digest,
            provider=manifest.target.provider,
            model=manifest.target.model,
            revision=manifest.target.revision,
            prompt_template_version=manifest.prompt_template_version,
            random_seed=manifest.random_seed,
            repetitions=manifest.repetitions,
            parameters=dict(manifest.parameters),
            plan_digest=manifest.plan_digest,
            status=ExperimentStatus.PLANNED.value,
            updated_at=manifest.created_at,
            task_id=None,
            last_error=None,
        )
        try:
            async with self._sessions.begin() as session:
                existing = await session.get(ExperimentRecord, manifest.experiment_id)
                if existing is not None:
                    if self._to_domain(existing) != manifest:
                        raise EvaluationError("experiment identifier collision")
                    return
                session.add(record)
        except IntegrityError as exc:
            raise EvaluationError("experiment persistence constraint failed") from exc

    async def get(self, experiment_id: UUID) -> ExperimentManifest | None:
        async with self._sessions() as session:
            record = await session.get(ExperimentRecord, experiment_id)
            return None if record is None else self._to_domain(record)

    async def get_state(self, experiment_id: UUID) -> ExperimentState | None:
        async with self._sessions() as session:
            record = await session.get(ExperimentRecord, experiment_id)
            return None if record is None else self._to_state(record)

    async def list_recent(
        self, limit: int = 100
    ) -> list[tuple[ExperimentManifest, ExperimentState]]:
        async with self._sessions() as session:
            records = (
                await session.execute(
                    select(ExperimentRecord)
                    .order_by(ExperimentRecord.created_at.desc())
                    .limit(limit)
                )
            ).scalars()
            return [(self._to_domain(record), self._to_state(record)) for record in records]

    async def transition(
        self,
        experiment_id: UUID,
        expected: ExperimentStatus,
        target: ExperimentStatus,
        *,
        task_id: str | None = None,
        last_error: str | None = None,
    ) -> ExperimentState:
        values: dict[str, object] = {
            "status": target.value,
            "updated_at": utc_now(),
            "last_error": last_error,
        }
        if task_id is not None:
            values["task_id"] = task_id
        async with self._sessions.begin() as session:
            result = await session.execute(
                update(ExperimentRecord)
                .where(
                    ExperimentRecord.experiment_id == experiment_id,
                    ExperimentRecord.status == expected.value,
                )
                .values(**values)
                .returning(ExperimentRecord)
            )
            record = result.scalar_one_or_none()
            if record is None:
                raise EvaluationError("experiment state transition conflict")
            return self._to_state(record)

    @staticmethod
    def _to_domain(record: ExperimentRecord) -> ExperimentManifest:
        return ExperimentManifest(
            experiment_id=record.experiment_id,
            created_at=record.created_at,
            problem_id=record.problem_id,
            statement_digest=record.statement_digest,
            test_suite_digest=record.test_suite_digest,
            target=ModelIdentity(record.provider, record.model, record.revision),
            prompt_template_version=record.prompt_template_version,
            random_seed=record.random_seed,
            repetitions=record.repetitions,
            parameters=tuple(sorted(record.parameters.items())),
        )

    @staticmethod
    def _to_state(record: ExperimentRecord) -> ExperimentState:
        return ExperimentState(
            experiment_id=record.experiment_id,
            status=ExperimentStatus(record.status),
            updated_at=record.updated_at,
            task_id=record.task_id,
            last_error=record.last_error,
        )
