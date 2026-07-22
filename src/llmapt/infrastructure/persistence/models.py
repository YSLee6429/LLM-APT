"""Control-plane relational persistence model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from llmapt.domain.experiments import ParameterValue


class Base(DeclarativeBase):
    pass


class ExperimentRecord(Base):
    __tablename__ = "experiments"

    experiment_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    problem_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    statement_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    test_suite_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(256), nullable=False)
    revision: Mapped[str | None] = mapped_column(String(256), nullable=True)
    prompt_template_version: Mapped[str] = mapped_column(String(128), nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False)
    parameters: Mapped[dict[str, ParameterValue]] = mapped_column(JSON, nullable=False)
    plan_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    last_error: Mapped[str | None] = mapped_column(String(4096), nullable=True)


class MutationCandidateRecord(Base):
    __tablename__ = "mutation_candidates"

    candidate_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    operator: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_problem_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    parent_statement_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_test_suite_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    problem_data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    oracle_validation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)


class OracleValidationRecord(Base):
    __tablename__ = "oracle_validations"

    validation_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    candidate_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("mutation_candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    oracle_key: Mapped[str] = mapped_column(String(128), nullable=False)
    oracle_version: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_problem_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_statement_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_statement_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_test_suite_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    cases: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)


class CandidateReviewRecord(Base):
    __tablename__ = "candidate_reviews"

    review_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    candidate_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("mutation_candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(128), nullable=False)
    justification: Mapped[str] = mapped_column(String(2000), nullable=False)


class ClosedLoopRecord(Base):
    __tablename__ = "closed_loop_reports"

    report_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    candidate_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("mutation_candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    evidence_level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    report_data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)


class WorkspaceUserRecord(Base):
    __tablename__ = "workspace_users"

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ProjectRecord(Base):
    __tablename__ = "projects"

    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspace_users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class ModelProfileRecord(Base):
    __tablename__ = "model_profiles"

    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(256), nullable=False)
    revision: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectResourceRecord(Base):
    __tablename__ = "project_resources"
    __table_args__ = (UniqueConstraint("project_id", "resource_type", "resource_id"),)

    link_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resource_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    linked_by: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspace_users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
