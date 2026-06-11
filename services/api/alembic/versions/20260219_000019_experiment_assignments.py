"""experiment assignments for ab testing

Revision ID: 20260219_000019
Revises: 20260215_000018
Create Date: 2026-02-19 00:00:19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260219_000019"
down_revision = "20260215_000018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "experiment_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("experiment_key", sa.String(length=64), nullable=False),
        sa.Column("variant_key", sa.String(length=64), nullable=False),
        sa.Column("assignment_hash", sa.String(length=128), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "experiment_key", name="ux_experiment_assignments_user_key"),
    )
    op.create_index(
        "ix_experiment_assignments_experiment_variant",
        "experiment_assignments",
        ["experiment_key", "variant_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_experiment_assignments_experiment_variant", table_name="experiment_assignments")
    op.drop_table("experiment_assignments")
