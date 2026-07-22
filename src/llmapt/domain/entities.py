"""Auditable immutable domain records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from llmapt.domain.enums import EvidenceLevel, Verdict


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    provider: str
    model: str
    revision: str | None = None


@dataclass(frozen=True, slots=True)
class RunManifest:
    target: ModelIdentity
    random_seed: int
    run_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    prompt_template_version: str = "unassigned"
    configuration_digest: str = "unassigned"


@dataclass(frozen=True, slots=True)
class FailureEvidence:
    verdict: Verdict
    level: EvidenceLevel
    input_digest: str
    expected_output_digest: str
    actual_output_digest: str
    repetitions: int
    evidence_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.repetitions < 1:
            raise ValueError("repetitions must be at least one")
        if self.level >= EvidenceLevel.REPRODUCIBLE_FAILURE and self.repetitions < 2:
            raise ValueError("reproducible evidence requires at least two observations")
