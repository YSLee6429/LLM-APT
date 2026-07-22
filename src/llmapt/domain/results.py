"""Evaluation results suitable for persistence and evidence review."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from llmapt.domain.enums import EvidenceLevel, Verdict


@dataclass(frozen=True, slots=True)
class CaseEvaluation:
    case_id: str
    verdict: Verdict
    input_digest: str
    expected_output_digest: str
    actual_output_digest: str
    duration_ms: int
    exit_code: int | None
    stderr_digest: str
    actual_output_artifact_uri: str
    stderr_artifact_uri: str


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    run_id: UUID
    problem_id: str
    model_provider: str
    model_name: str
    verdict: Verdict
    evidence_level: EvidenceLevel
    cases: tuple[CaseEvaluation, ...]
    source_artifact_uri: str
    response_artifact_uri: str
    compile_diagnostics_artifact_uri: str
    report_artifact_uri: str | None = None

    @property
    def passed_cases(self) -> int:
        return sum(case.verdict is Verdict.ACCEPTED for case in self.cases)

    @property
    def total_cases(self) -> int:
        return len(self.cases)
