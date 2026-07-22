"""PostgreSQL candidate and oracle-validation repositories."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from llmapt.domain.entities import utc_now
from llmapt.domain.enums import (
    CandidateStatus,
    MutationKind,
    OracleValidationVerdict,
    OutputPolicy,
)
from llmapt.domain.errors import EvaluationError
from llmapt.domain.mutations import CandidateState, MutationCandidate
from llmapt.domain.oracles import (
    OracleCaseValidation,
    OracleIdentity,
    OracleValidationReport,
)
from llmapt.domain.problems import ProblemSpec, ResourceLimits, TestCase
from llmapt.domain.state_machine import require_transition
from llmapt.infrastructure.persistence.models import (
    MutationCandidateRecord,
    OracleValidationRecord,
)


class PostgresCandidateRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, candidate: MutationCandidate) -> None:
        record = MutationCandidateRecord(
            candidate_id=candidate.candidate_id,
            created_at=candidate.created_at,
            operator=candidate.operator.value,
            parent_problem_id=candidate.parent_problem_id,
            parent_statement_digest=candidate.parent_statement_digest,
            parent_test_suite_digest=candidate.parent_test_suite_digest,
            random_seed=candidate.random_seed,
            notes=list(candidate.notes),
            problem_data=_problem_to_json(candidate.problem),
            status=CandidateStatus.GENERATED.value,
            updated_at=candidate.created_at,
            oracle_validation_id=None,
            reason_code=None,
        )
        try:
            async with self._sessions.begin() as session:
                existing = await session.get(MutationCandidateRecord, candidate.candidate_id)
                if existing is not None:
                    if _candidate_to_domain(existing) != candidate:
                        raise EvaluationError("candidate identifier collision")
                    return
                session.add(record)
        except IntegrityError as exc:
            raise EvaluationError("candidate persistence constraint failed") from exc

    async def get(self, candidate_id: UUID) -> MutationCandidate | None:
        async with self._sessions() as session:
            record = await session.get(MutationCandidateRecord, candidate_id)
            return None if record is None else _candidate_to_domain(record)

    async def get_state(self, candidate_id: UUID) -> CandidateState | None:
        async with self._sessions() as session:
            record = await session.get(MutationCandidateRecord, candidate_id)
            return None if record is None else _candidate_to_state(record)

    async def list_recent(self, limit: int = 100) -> list[tuple[MutationCandidate, CandidateState]]:
        async with self._sessions() as session:
            records = (
                await session.execute(
                    select(MutationCandidateRecord)
                    .order_by(MutationCandidateRecord.created_at.desc())
                    .limit(limit)
                )
            ).scalars()
            return [
                (_candidate_to_domain(record), _candidate_to_state(record)) for record in records
            ]

    async def transition(
        self,
        candidate_id: UUID,
        expected: CandidateStatus,
        target: CandidateStatus,
        *,
        oracle_validation_id: UUID | None = None,
        reason_code: str | None = None,
    ) -> CandidateState:
        require_transition(expected, target)
        values: dict[str, object] = {
            "status": target.value,
            "updated_at": utc_now(),
            "reason_code": reason_code,
        }
        if oracle_validation_id is not None:
            values["oracle_validation_id"] = oracle_validation_id
        async with self._sessions.begin() as session:
            result = await session.execute(
                update(MutationCandidateRecord)
                .where(
                    MutationCandidateRecord.candidate_id == candidate_id,
                    MutationCandidateRecord.status == expected.value,
                )
                .values(**values)
                .returning(MutationCandidateRecord)
            )
            record = result.scalar_one_or_none()
            if record is None:
                raise EvaluationError("candidate state transition conflict")
            return _candidate_to_state(record)


class PostgresOracleValidationRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, report: OracleValidationReport) -> None:
        record = OracleValidationRecord(
            validation_id=report.validation_id,
            candidate_id=report.candidate_id,
            created_at=report.created_at,
            oracle_key=report.oracle.key,
            oracle_version=report.oracle.version,
            parent_problem_id=report.oracle.parent_problem_id,
            parent_statement_digest=report.oracle.parent_statement_digest,
            language=report.oracle.language,
            candidate_statement_digest=report.candidate_statement_digest,
            candidate_test_suite_digest=report.candidate_test_suite_digest,
            verdict=report.verdict.value,
            cases=[_oracle_case_to_json(case) for case in report.cases],
            reason_code=report.reason_code,
        )
        try:
            async with self._sessions.begin() as session:
                existing = await session.get(OracleValidationRecord, report.validation_id)
                if existing is not None:
                    if _oracle_report_to_domain(existing) != report:
                        raise EvaluationError("oracle validation identifier collision")
                    return
                session.add(record)
        except IntegrityError as exc:
            raise EvaluationError("oracle validation persistence constraint failed") from exc

    async def get(self, validation_id: UUID) -> OracleValidationReport | None:
        async with self._sessions() as session:
            record = await session.get(OracleValidationRecord, validation_id)
            return None if record is None else _oracle_report_to_domain(record)

    async def latest_for_candidate(self, candidate_id: UUID) -> OracleValidationReport | None:
        async with self._sessions() as session:
            record = (
                await session.execute(
                    select(OracleValidationRecord)
                    .where(OracleValidationRecord.candidate_id == candidate_id)
                    .order_by(OracleValidationRecord.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            return None if record is None else _oracle_report_to_domain(record)


def _problem_to_json(problem: ProblemSpec) -> dict[str, object]:
    return {
        "problem_id": problem.problem_id,
        "title": problem.title,
        "statement": problem.statement,
        "language": problem.language,
        "output_policy": problem.output_policy.value,
        "limits": {
            "time_limit_ms": problem.limits.time_limit_ms,
            "memory_limit_mb": problem.limits.memory_limit_mb,
            "process_limit": problem.limits.process_limit,
            "output_limit_bytes": problem.limits.output_limit_bytes,
        },
        "tests": [
            {
                "case_id": case.case_id,
                "standard_input_hex": case.standard_input.hex(),
                "expected_output_hex": case.expected_output.hex(),
                "hidden": case.hidden,
            }
            for case in problem.tests
        ],
    }


def _problem_from_json(data: dict[str, object]) -> ProblemSpec:
    limits = cast(dict[str, object], data["limits"])
    tests = cast(list[dict[str, object]], data["tests"])
    return ProblemSpec(
        problem_id=str(data["problem_id"]),
        title=str(data["title"]),
        statement=str(data["statement"]),
        language=str(data["language"]),
        output_policy=OutputPolicy(str(data["output_policy"])),
        limits=ResourceLimits(
            time_limit_ms=int(cast(int, limits["time_limit_ms"])),
            memory_limit_mb=int(cast(int, limits["memory_limit_mb"])),
            process_limit=int(cast(int, limits["process_limit"])),
            output_limit_bytes=int(cast(int, limits["output_limit_bytes"])),
        ),
        tests=tuple(
            TestCase(
                case_id=str(item["case_id"]),
                standard_input=bytes.fromhex(str(item["standard_input_hex"])),
                expected_output=bytes.fromhex(str(item["expected_output_hex"])),
                hidden=bool(item["hidden"]),
            )
            for item in tests
        ),
    )


def _candidate_to_domain(record: MutationCandidateRecord) -> MutationCandidate:
    return MutationCandidate(
        candidate_id=record.candidate_id,
        created_at=record.created_at,
        operator=MutationKind(record.operator),
        parent_problem_id=record.parent_problem_id,
        parent_statement_digest=record.parent_statement_digest,
        parent_test_suite_digest=record.parent_test_suite_digest,
        problem=_problem_from_json(record.problem_data),
        random_seed=record.random_seed,
        notes=tuple(record.notes),
    )


def _candidate_to_state(record: MutationCandidateRecord) -> CandidateState:
    return CandidateState(
        candidate_id=record.candidate_id,
        status=CandidateStatus(record.status),
        updated_at=record.updated_at,
        oracle_validation_id=record.oracle_validation_id,
        reason_code=record.reason_code,
    )


def _oracle_case_to_json(case: OracleCaseValidation) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "input_digest": case.input_digest,
        "expected_output_digest": case.expected_output_digest,
        "actual_output_digest": case.actual_output_digest,
        "matched": case.matched,
        "reason_code": case.reason_code,
    }


def _oracle_report_to_domain(record: OracleValidationRecord) -> OracleValidationReport:
    return OracleValidationReport(
        validation_id=record.validation_id,
        candidate_id=record.candidate_id,
        created_at=record.created_at,
        oracle=OracleIdentity(
            key=record.oracle_key,
            version=record.oracle_version,
            parent_problem_id=record.parent_problem_id,
            parent_statement_digest=record.parent_statement_digest,
            language=record.language,
        ),
        candidate_statement_digest=record.candidate_statement_digest,
        candidate_test_suite_digest=record.candidate_test_suite_digest,
        verdict=OracleValidationVerdict(record.verdict),
        cases=tuple(
            OracleCaseValidation(
                case_id=str(item["case_id"]),
                input_digest=str(item["input_digest"]),
                expected_output_digest=str(item["expected_output_digest"]),
                actual_output_digest=str(item["actual_output_digest"]),
                matched=bool(item["matched"]),
                reason_code=(None if item.get("reason_code") is None else str(item["reason_code"])),
            )
            for item in record.cases
        ),
        reason_code=record.reason_code,
    )
