"""trust safety risk and message safety flags

Revision ID: 20260215_000017
Revises: 20260215_000016
Create Date: 2026-02-15 00:00:17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260215_000017"
down_revision = "20260215_000016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trust_safety_risks",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_band", sa.String(length=16), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "safety_action_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_safety_action_logs_user_created", "safety_action_logs", ["user_id", "created_at"])

    op.add_column("messages", sa.Column("hidden_by_safety", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("messages", "hidden_by_safety", server_default=None)


def downgrade() -> None:
    op.drop_column("messages", "hidden_by_safety")

    op.drop_index("ix_safety_action_logs_user_created", table_name="safety_action_logs")
    op.drop_table("safety_action_logs")

    op.drop_table("trust_safety_risks")
