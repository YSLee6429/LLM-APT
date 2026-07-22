"""Create persistent experiment manifests.

Revision ID: 20260721_0001
Revises:
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("problem_id", sa.String(length=128), nullable=False),
        sa.Column("statement_digest", sa.String(length=64), nullable=False),
        sa.Column("test_suite_digest", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=256), nullable=False),
        sa.Column("revision", sa.String(length=256), nullable=True),
        sa.Column("prompt_template_version", sa.String(length=128), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=False),
        sa.Column("repetitions", sa.Integer(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("plan_digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.String(length=4096), nullable=True),
        sa.PrimaryKeyConstraint("experiment_id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index("ix_experiments_plan_digest", "experiments", ["plan_digest"])
    op.create_index("ix_experiments_problem_id", "experiments", ["problem_id"])
    op.create_index("ix_experiments_status", "experiments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_experiments_status", table_name="experiments")
    op.drop_index("ix_experiments_problem_id", table_name="experiments")
    op.drop_index("ix_experiments_plan_digest", table_name="experiments")
    op.drop_table("experiments")
