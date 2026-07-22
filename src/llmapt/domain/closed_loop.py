"""Closed-loop execution evidence and minimized counterexamples."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from llmapt.domain.entities import ModelIdentity, utc_now
from llmapt.domain.enums import EvidenceLevel, Verdict


@dataclass(frozen=True, slots=True)
class RepetitionObservation:
    repetition: int
    source_digest: str
    raw_response_digest: str
    source_text: str
    raw_response_text: str
    verdict: Verdict
    failure_case_id: str | None = None
    input_digest: str | None = None
    expected_output_digest: str | None = None
    actual_output_digest: str | None = None
    actual_output: bytes = b""


@dataclass(frozen=True, slots=True)
class Counterexample:
    case_id: str
    original_input_digest: str
    minimized_input_digest: str
    minimized_input: bytes
    expected_output_digest: str
    actual_output_digest: str
    original_size: int
    minimized_size: int
    attempts: int


@dataclass(frozen=True, slots=True)
class ClosedLoopReport:
    candidate_id: UUID
    oracle_validation_id: UUID
    target: ModelIdentity
    repetitions_requested: int
    repetitions_completed: int
    verdict: Verdict
    evidence_level: EvidenceLevel
    stable_failure: bool
    observations: tuple[RepetitionObservation, ...]
    counterexample: Counterexample | None = None
    report_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
