"""PostgreSQL human-review and closed-loop report repositories."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from llmapt.domain.closed_loop import (
    ClosedLoopReport,
    Counterexample,
    RepetitionObservation,
)
from llmapt.domain.entities import ModelIdentity
from llmapt.domain.enums import EvidenceLevel, ReviewDecision, Verdict
from llmapt.domain.errors import EvaluationError
from llmapt.domain.reviews import CandidateReview
from llmapt.infrastructure.persistence.models import CandidateReviewRecord, ClosedLoopRecord


class PostgresCandidateReviewRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, review: CandidateReview) -> None:
        try:
            async with self._sessions.begin() as session:
                session.add(
                    CandidateReviewRecord(
                        review_id=review.review_id,
                        candidate_id=review.candidate_id,
                        created_at=review.created_at,
                        decision=review.decision.value,
                        reviewer=review.reviewer,
                        justification=review.justification,
                    )
                )
        except IntegrityError as exc:
            raise EvaluationError("candidate review persistence constraint failed") from exc

    async def latest_for_candidate(self, candidate_id: UUID) -> CandidateReview | None:
        async with self._sessions() as session:
            record = (
                await session.execute(
                    select(CandidateReviewRecord)
                    .where(CandidateReviewRecord.candidate_id == candidate_id)
                    .order_by(CandidateReviewRecord.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            return None if record is None else _review_to_domain(record)


class PostgresClosedLoopRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, report: ClosedLoopReport) -> None:
        try:
            async with self._sessions.begin() as session:
                session.add(
                    ClosedLoopRecord(
                        report_id=report.report_id,
                        candidate_id=report.candidate_id,
                        created_at=report.created_at,
                        verdict=report.verdict.value,
                        evidence_level=int(report.evidence_level),
                        report_data=_report_to_json(report),
                    )
                )
        except IntegrityError as exc:
            raise EvaluationError("closed-loop report persistence constraint failed") from exc

    async def get(self, report_id: UUID) -> ClosedLoopReport | None:
        async with self._sessions() as session:
            record = await session.get(ClosedLoopRecord, report_id)
            return None if record is None else _report_from_json(record.report_data)

    async def list_recent(self, limit: int = 100) -> list[ClosedLoopReport]:
        async with self._sessions() as session:
            records = (
                await session.execute(
                    select(ClosedLoopRecord)
                    .order_by(ClosedLoopRecord.created_at.desc())
                    .limit(limit)
                )
            ).scalars()
            return [_report_from_json(record.report_data) for record in records]


def _review_to_domain(record: CandidateReviewRecord) -> CandidateReview:
    return CandidateReview(
        review_id=record.review_id,
        candidate_id=record.candidate_id,
        created_at=record.created_at,
        decision=ReviewDecision(record.decision),
        reviewer=record.reviewer,
        justification=record.justification,
    )


def _report_to_json(report: ClosedLoopReport) -> dict[str, object]:
    return {
        "report_id": str(report.report_id),
        "candidate_id": str(report.candidate_id),
        "oracle_validation_id": str(report.oracle_validation_id),
        "created_at": report.created_at.isoformat(),
        "target": {
            "provider": report.target.provider,
            "model": report.target.model,
            "revision": report.target.revision,
        },
        "repetitions_requested": report.repetitions_requested,
        "repetitions_completed": report.repetitions_completed,
        "verdict": report.verdict.value,
        "evidence_level": int(report.evidence_level),
        "stable_failure": report.stable_failure,
        "observations": [
            {
                "repetition": item.repetition,
                "source_digest": item.source_digest,
                "raw_response_digest": item.raw_response_digest,
                "source_text": item.source_text,
                "raw_response_text": item.raw_response_text,
                "verdict": item.verdict.value,
                "failure_case_id": item.failure_case_id,
                "input_digest": item.input_digest,
                "expected_output_digest": item.expected_output_digest,
                "actual_output_digest": item.actual_output_digest,
                "actual_output_hex": item.actual_output.hex(),
            }
            for item in report.observations
        ],
        "counterexample": None
        if report.counterexample is None
        else {
            "case_id": report.counterexample.case_id,
            "original_input_digest": report.counterexample.original_input_digest,
            "minimized_input_digest": report.counterexample.minimized_input_digest,
            "minimized_input_hex": report.counterexample.minimized_input.hex(),
            "expected_output_digest": report.counterexample.expected_output_digest,
            "actual_output_digest": report.counterexample.actual_output_digest,
            "original_size": report.counterexample.original_size,
            "minimized_size": report.counterexample.minimized_size,
            "attempts": report.counterexample.attempts,
        },
    }


def _report_from_json(data: dict[str, object]) -> ClosedLoopReport:
    from datetime import datetime

    target = cast(dict[str, object], data["target"])
    observations = cast(list[dict[str, object]], data["observations"])
    counterexample_data = cast(dict[str, object] | None, data["counterexample"])
    return ClosedLoopReport(
        report_id=UUID(str(data["report_id"])),
        candidate_id=UUID(str(data["candidate_id"])),
        oracle_validation_id=UUID(str(data["oracle_validation_id"])),
        created_at=datetime.fromisoformat(str(data["created_at"])),
        target=ModelIdentity(
            provider=str(target["provider"]),
            model=str(target["model"]),
            revision=None if target["revision"] is None else str(target["revision"]),
        ),
        repetitions_requested=int(cast(int, data["repetitions_requested"])),
        repetitions_completed=int(cast(int, data["repetitions_completed"])),
        verdict=Verdict(str(data["verdict"])),
        evidence_level=EvidenceLevel(int(cast(int, data["evidence_level"]))),
        stable_failure=bool(data["stable_failure"]),
        observations=tuple(
            RepetitionObservation(
                repetition=int(cast(int, item["repetition"])),
                source_digest=str(item["source_digest"]),
                raw_response_digest=str(item["raw_response_digest"]),
                source_text=str(item["source_text"]),
                raw_response_text=str(item["raw_response_text"]),
                verdict=Verdict(str(item["verdict"])),
                failure_case_id=_optional_string(item.get("failure_case_id")),
                input_digest=_optional_string(item.get("input_digest")),
                expected_output_digest=_optional_string(item.get("expected_output_digest")),
                actual_output_digest=_optional_string(item.get("actual_output_digest")),
                actual_output=bytes.fromhex(str(item["actual_output_hex"])),
            )
            for item in observations
        ),
        counterexample=None
        if counterexample_data is None
        else Counterexample(
            case_id=str(counterexample_data["case_id"]),
            original_input_digest=str(counterexample_data["original_input_digest"]),
            minimized_input_digest=str(counterexample_data["minimized_input_digest"]),
            minimized_input=bytes.fromhex(str(counterexample_data["minimized_input_hex"])),
            expected_output_digest=str(counterexample_data["expected_output_digest"]),
            actual_output_digest=str(counterexample_data["actual_output_digest"]),
            original_size=int(cast(int, counterexample_data["original_size"])),
            minimized_size=int(cast(int, counterexample_data["minimized_size"])),
            attempts=int(cast(int, counterexample_data["attempts"])),
        ),
    )


def _optional_string(value: object) -> str | None:
    return None if value is None else str(value)
