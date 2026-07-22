"""Domain exceptions that do not expose infrastructure details."""


class DomainError(Exception):
    """Base class for deterministic domain rule violations."""


class InvalidTransitionError(DomainError):
    """Raised when a candidate workflow transition is not allowed."""


class InvalidProblemError(DomainError):
    """Raised when a problem or test-case definition violates the schema."""


class EvaluationError(DomainError):
    """Raised when an evaluation request cannot be completed deterministically."""
