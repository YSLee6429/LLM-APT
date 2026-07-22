"""SQLAlchemy persistence adapters."""

from llmapt.infrastructure.persistence.candidates import (
    PostgresCandidateRepository,
    PostgresOracleValidationRepository,
)
from llmapt.infrastructure.persistence.closed_loop import (
    PostgresCandidateReviewRepository,
    PostgresClosedLoopRepository,
)
from llmapt.infrastructure.persistence.experiments import PostgresExperimentRepository
from llmapt.infrastructure.persistence.models import (
    Base,
    CandidateReviewRecord,
    ClosedLoopRecord,
    ExperimentRecord,
    MutationCandidateRecord,
    OracleValidationRecord,
)

__all__ = [
    "Base",
    "CandidateReviewRecord",
    "ClosedLoopRecord",
    "ExperimentRecord",
    "MutationCandidateRecord",
    "OracleValidationRecord",
    "PostgresCandidateRepository",
    "PostgresCandidateReviewRepository",
    "PostgresClosedLoopRepository",
    "PostgresExperimentRepository",
    "PostgresOracleValidationRepository",
]
