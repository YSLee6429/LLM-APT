import pytest

from llmapt.domain.entities import FailureEvidence
from llmapt.domain.enums import EvidenceLevel, Verdict


def test_reproducible_failure_requires_two_observations() -> None:
    with pytest.raises(ValueError, match="at least two"):
        FailureEvidence(
            verdict=Verdict.WRONG_ANSWER,
            level=EvidenceLevel.REPRODUCIBLE_FAILURE,
            input_digest="input",
            expected_output_digest="expected",
            actual_output_digest="actual",
            repetitions=1,
        )


def test_reproducible_failure_accepts_two_observations() -> None:
    evidence = FailureEvidence(
        verdict=Verdict.WRONG_ANSWER,
        level=EvidenceLevel.REPRODUCIBLE_FAILURE,
        input_digest="input",
        expected_output_digest="expected",
        actual_output_digest="actual",
        repetitions=2,
    )

    assert evidence.repetitions == 2
