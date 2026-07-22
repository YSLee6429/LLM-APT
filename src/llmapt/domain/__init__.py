"""Framework-independent domain model."""

from llmapt.domain.entities import FailureEvidence, ModelIdentity, RunManifest
from llmapt.domain.enums import CandidateStatus, EvidenceLevel, OutputPolicy, Verdict
from llmapt.domain.problems import ProblemSpec, ResourceLimits, TestCase
from llmapt.domain.results import CaseEvaluation, EvaluationReport

__all__ = [
    "CandidateStatus",
    "CaseEvaluation",
    "EvaluationReport",
    "EvidenceLevel",
    "FailureEvidence",
    "ModelIdentity",
    "OutputPolicy",
    "ProblemSpec",
    "ResourceLimits",
    "RunManifest",
    "TestCase",
    "Verdict",
]
