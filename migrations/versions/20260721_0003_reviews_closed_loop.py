"""Create candidate review and closed-loop report records.

Revision ID: 20260721_0003
Revises: 20260721_0002
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0003"
down_revision: str | None = "20260721_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_reviews",
        sa.Column("review_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("reviewer", sa.String(length=128), nullable=False),
        sa.Column("justification", sa.String(length=2000), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["mutation_candidates.candidate_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("review_id"),
    )
    op.create_index("ix_candidate_reviews_candidate_id", "candidate_reviews", ["candidate_id"])
    op.create_index("ix_candidate_reviews_decision", "candidate_reviews", ["decision"])

    op.create_table(
        "closed_loop_reports",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("evidence_level", sa.Integer(), nullable=False),
        sa.Column("report_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["mutation_candidates.candidate_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("report_id"),
    )
    op.create_index("ix_closed_loop_reports_candidate_id", "closed_loop_reports", ["candidate_id"])
    op.create_index("ix_closed_loop_reports_verdict", "closed_loop_reports", ["verdict"])
    op.create_index(
        "ix_closed_loop_reports_evidence_level", "closed_loop_reports", ["evidence_level"]
    )


def downgrade() -> None:
    op.drop_index("ix_closed_loop_reports_evidence_level", table_name="closed_loop_reports")
    op.drop_index("ix_closed_loop_reports_verdict", table_name="closed_loop_reports")
    op.drop_index("ix_closed_loop_reports_candidate_id", table_name="closed_loop_reports")
    op.drop_table("closed_loop_reports")
    op.drop_index("ix_candidate_reviews_decision", table_name="candidate_reviews")
    op.drop_index("ix_candidate_reviews_candidate_id", table_name="candidate_reviews")
    op.drop_table("candidate_reviews")
