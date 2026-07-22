from datetime import UTC, datetime
from uuid import uuid4

from llmapt.domain.closed_loop import ClosedLoopReport, Counterexample, RepetitionObservation
from llmapt.domain.entities import ModelIdentity
from llmapt.domain.enums import EvidenceLevel, ReviewDecision, Verdict
from llmapt.domain.reviews import CandidateReview
from llmapt.infrastructure.persistence.closed_loop import (
    _report_from_json,
    _report_to_json,
    _review_to_domain,
)
from llmapt.infrastructure.persistence.models import CandidateReviewRecord


def test_closed_loop_report_json_round_trip_preserves_private_evidence() -> None:
    report = ClosedLoopReport(
        candidate_id=uuid4(),
        oracle_validation_id=uuid4(),
        target=ModelIdentity("local", "coder", "m2"),
        repetitions_requested=2,
        repetitions_completed=2,
        verdict=Verdict.WRONG_ANSWER,
        evidence_level=EvidenceLevel.REPRODUCIBLE_FAILURE,
        stable_failure=True,
        observations=(
            RepetitionObservation(
                repetition=1,
                source_digest="a" * 64,
                raw_response_digest="b" * 64,
                source_text="int main(){}",
                raw_response_text="```cpp\nint main(){}\n```",
                verdict=Verdict.WRONG_ANSWER,
                failure_case_id="negative",
                input_digest="c" * 64,
                expected_output_digest="d" * 64,
                actual_output_digest="e" * 64,
                actual_output=b"0\n",
            ),
        ),
        counterexample=Counterexample(
            case_id="negative",
            original_input_digest="f" * 64,
            minimized_input_digest="1" * 64,
            minimized_input=b"-3",
            expected_output_digest="2" * 64,
            actual_output_digest="3" * 64,
            original_size=3,
            minimized_size=2,
            attempts=1,
        ),
    )

    assert _report_from_json(_report_to_json(report)) == report


def test_review_record_mapping() -> None:
    review = CandidateReview(
        candidate_id=uuid4(),
        decision=ReviewDecision.APPROVE,
        reviewer="reviewer",
        justification="checked",
    )
    record = CandidateReviewRecord(
        review_id=review.review_id,
        candidate_id=review.candidate_id,
        created_at=datetime.now(UTC),
        decision=review.decision.value,
        reviewer=review.reviewer,
        justification=review.justification,
    )

    restored = _review_to_domain(record)
    assert restored.review_id == review.review_id
    assert restored.decision is ReviewDecision.APPROVE
