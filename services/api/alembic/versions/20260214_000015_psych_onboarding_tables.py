"""psych onboarding tables

Revision ID: 20260214_000015
Revises: 20260214_000014
Create Date: 2026-02-14 00:00:15
"""

from alembic import op
import sqlalchemy as sa


revision = "20260214_000015"
down_revision = "20260214_000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "psych_profiles",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("ocean_vector", sa.JSON(), nullable=False),
        sa.Column("attachment_style", sa.String(length=32), nullable=False),
        sa.Column("attachment_confidence", sa.Float(), nullable=False),
        sa.Column("love_language", sa.String(length=64), nullable=False),
        sa.Column("communication_style", sa.String(length=64), nullable=False),
        sa.Column("conflict_style", sa.String(length=64), nullable=False),
        sa.Column("social_energy", sa.String(length=32), nullable=False),
        sa.Column("novelty_preference", sa.Float(), nullable=False),
        sa.Column("boundaries_preference", sa.Float(), nullable=False),
        sa.Column("source_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "onboarding_answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("section", sa.String(length=64), nullable=False),
        sa.Column("question_id", sa.String(length=64), nullable=False),
        sa.Column("answer", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_onboarding_answers_user_section", "onboarding_answers", ["user_id", "section"])


def downgrade() -> None:
    op.drop_index("ix_onboarding_answers_user_section", table_name="onboarding_answers")
    op.drop_table("onboarding_answers")
    op.drop_table("psych_profiles")
