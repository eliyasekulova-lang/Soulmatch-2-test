"""add web_assessments table

Revision ID: 000028
Revises: 000027
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa

revision = "000028"
down_revision = "000027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_assessments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("mode", sa.String(32), nullable=True),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("adaptive_answer", sa.Integer(), nullable=True),
        sa.Column("attachment_type", sa.String(32), nullable=True),
        sa.Column("dimension_scores", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_web_assessments_email", "web_assessments", ["email"])


def downgrade() -> None:
    op.drop_index("ix_web_assessments_email", table_name="web_assessments")
    op.drop_table("web_assessments")
