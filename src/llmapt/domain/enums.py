"""Stable domain enumerations persisted in manifests and events."""

from enum import IntEnum, StrEnum


class CandidateStatus(StrEnum):
    GENERATED = "generated"
    STRUCTURE_VALIDATED = "structure_validated"
    ORACLE_VALIDATED = "oracle_validated"
    READY = "ready"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    ANALYZED = "analyzed"
    RETRY_WAIT = "retry_wait"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


class Verdict(StrEnum):
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    COMPILE_ERROR = "compile_error"
    RUNTIME_ERROR = "runtime_error"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    OUTPUT_LIMIT_EXCEEDED = "output_limit_exceeded"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    INCONCLUSIVE = "inconclusive"


class OutputPolicy(StrEnum):
    """Supported deterministic output comparison policies."""

    EXACT = "exact"
    TRIM_TRAILING_WHITESPACE = "trim_trailing_whitespace"
    TOKEN = "token"


class EvidenceLevel(IntEnum):
    NONE = 0
    OBSERVED_DIFFERENCE = 1
    REPRODUCIBLE_FAILURE = 2
    REVIEWED_MINIMAL_CASE = 3
    CROSS_TASK_REPLICATION = 4


class ExperimentStatus(StrEnum):
    PLANNED = "planned"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MutationKind(StrEnum):
    TEST_ORDER_ROTATION = "test_order_rotation"
    BOUNDARY_CLAUSE = "boundary_clause"
    OUTPUT_POLICY_EXACT = "output_policy_exact"


class OracleValidationVerdict(StrEnum):
    PASSED = "passed"
    REJECTED = "rejected"
    ERROR = "error"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
