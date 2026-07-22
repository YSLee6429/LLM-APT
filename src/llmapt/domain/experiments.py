"""Immutable experiment plans used to reproduce model-generation campaigns."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from llmapt.domain.digests import digest_mapping
from llmapt.domain.entities import ModelIdentity, utc_now
from llmapt.domain.enums import ExperimentStatus

ParameterValue = str | int | float | bool


@dataclass(frozen=True, slots=True)
class ExperimentManifest:
    """Canonical plan shared by every run in one experiment."""

    problem_id: str
    statement_digest: str
    test_suite_digest: str
    target: ModelIdentity
    prompt_template_version: str
    random_seed: int
    repetitions: int
    parameters: tuple[tuple[str, ParameterValue], ...] = ()
    experiment_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.problem_id.strip():
            raise ValueError("problem_id must not be blank")
        if not self.prompt_template_version.strip():
            raise ValueError("prompt_template_version must not be blank")
        if not 1 <= self.repetitions <= 100:
            raise ValueError("repetitions must be between 1 and 100")
        keys = [key for key, _value in self.parameters]
        if any(not key.strip() for key in keys):
            raise ValueError("parameter names must not be blank")
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("parameters must be unique and sorted by name")

    @property
    def plan_digest(self) -> str:
        values: dict[str, ParameterValue] = {
            "problem_id": self.problem_id,
            "statement_digest": self.statement_digest,
            "test_suite_digest": self.test_suite_digest,
            "provider": self.target.provider,
            "model": self.target.model,
            "revision": self.target.revision or "",
            "prompt_template_version": self.prompt_template_version,
            "random_seed": self.random_seed,
            "repetitions": self.repetitions,
        }
        values.update({f"model.{key}": value for key, value in self.parameters})
        return digest_mapping(values)


@dataclass(frozen=True, slots=True)
class ExperimentState:
    experiment_id: UUID
    status: ExperimentStatus
    updated_at: datetime
    task_id: str | None = None
    last_error: str | None = None
