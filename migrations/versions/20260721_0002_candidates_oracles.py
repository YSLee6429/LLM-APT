"""Create mutation candidate and oracle validation records.

Revision ID: 20260721_0002
Revises: 20260721_0001
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0002"
down_revision: str | None = "20260721_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mutation_candidates",
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("operator", sa.String(length=64), nullable=False),
        sa.Column("parent_problem_id", sa.String(length=128), nullable=False),
        sa.Column("parent_statement_digest", sa.String(length=64), nullable=False),
        sa.Column("parent_test_suite_digest", sa.String(length=64), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("problem_data", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("oracle_validation_id", sa.Uuid(), nullable=True),
        sa.Column("reason_code", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("candidate_id"),
    )
    op.create_index("ix_mutation_candidates_operator", "mutation_candidates", ["operator"])
    op.create_index(
        "ix_mutation_candidates_parent_problem_id",
        "mutation_candidates",
        ["parent_problem_id"],
    )
    op.create_index("ix_mutation_candidates_status", "mutation_candidates", ["status"])

    op.create_table(
        "oracle_validations",
        sa.Column("validation_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("oracle_key", sa.String(length=128), nullable=False),
        sa.Column("oracle_version", sa.String(length=128), nullable=False),
        sa.Column("parent_problem_id", sa.String(length=128), nullable=False),
        sa.Column("parent_statement_digest", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("candidate_statement_digest", sa.String(length=64), nullable=False),
        sa.Column("candidate_test_suite_digest", sa.String(length=64), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("cases", sa.JSON(), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["mutation_candidates.candidate_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("validation_id"),
    )
    op.create_index("ix_oracle_validations_candidate_id", "oracle_validations", ["candidate_id"])
    op.create_index("ix_oracle_validations_verdict", "oracle_validations", ["verdict"])


def downgrade() -> None:
    op.drop_index("ix_oracle_validations_verdict", table_name="oracle_validations")
    op.drop_index("ix_oracle_validations_candidate_id", table_name="oracle_validations")
    op.drop_table("oracle_validations")
    op.drop_index("ix_mutation_candidates_status", table_name="mutation_candidates")
    op.drop_index("ix_mutation_candidates_parent_problem_id", table_name="mutation_candidates")
    op.drop_index("ix_mutation_candidates_operator", table_name="mutation_candidates")
    op.drop_table("mutation_candidates")
