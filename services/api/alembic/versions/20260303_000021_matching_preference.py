"""add matching preference to users

Revision ID: 20260303_000021
Revises: 20260303_000020
Create Date: 2026-03-03 00:00:21
"""

from alembic import op
import sqlalchemy as sa

revision = "20260303_000021"
down_revision = "20260303_000020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("matching_preference", sa.String(length=32), nullable=False, server_default="psych_behavior_astro"),
    )
    op.execute("UPDATE users SET matching_preference = 'psych_behavior_astro' WHERE matching_preference IS NULL")
    op.alter_column("users", "matching_preference", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "matching_preference")
