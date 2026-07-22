"""Auditable results produced only by registered trusted oracles."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from llmapt.domain.entities import utc_now
from llmapt.domain.enums import OracleValidationVerdict


@dataclass(frozen=True, slots=True)
class OracleIdentity:
    key: str
    version: str
    parent_problem_id: str
    parent_statement_digest: str
    language: str


@dataclass(frozen=True, slots=True)
class OracleCaseValidation:
    case_id: str
    input_digest: str
    expected_output_digest: str
    actual_output_digest: str
    matched: bool
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class OracleValidationReport:
    candidate_id: UUID
    oracle: OracleIdentity
    candidate_statement_digest: str
    candidate_test_suite_digest: str
    verdict: OracleValidationVerdict
    cases: tuple[OracleCaseValidation, ...]
    reason_code: str | None = None
    validation_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)

    @property
    def passed_cases(self) -> int:
        return sum(case.matched for case in self.cases)
