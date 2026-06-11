"""behavior learning tables

Revision ID: 20260215_000016
Revises: 20260214_000015
Create Date: 2026-02-15 00:00:16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260215_000016"
down_revision = "20260214_000015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "behavior_signal_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_behavior_signal_events_user_created", "behavior_signal_events", ["user_id", "created_at"])

    op.create_table(
        "behavior_profiles",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("reply_time_score", sa.Float(), nullable=False),
        sa.Column("conversation_depth_score", sa.Float(), nullable=False),
        sa.Column("consistency_score", sa.Float(), nullable=False),
        sa.Column("receptiveness_score", sa.Float(), nullable=False),
        sa.Column("boundary_respect_score", sa.Float(), nullable=False),
        sa.Column("initiation_balance_score", sa.Float(), nullable=False),
        sa.Column("behavior_vector", sa.JSON(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("behavior_profiles")
    op.drop_index("ix_behavior_signal_events_user_created", table_name="behavior_signal_events")
    op.drop_table("behavior_signal_events")
