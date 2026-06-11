"""runtime observability tables

Revision ID: 20260215_000018
Revises: 20260215_000017
Create Date: 2026-02-15 00:00:18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260215_000018"
down_revision = "20260215_000017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_run_telemetry",
        sa.Column("job_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=False),
        sa.Column("run_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("job_name"),
    )


def downgrade() -> None:
    op.drop_table("job_run_telemetry")
