"""separate compatibility score from rank-facing match score

Revision ID: 20260424_000026
Revises: 20260424_000025
Create Date: 2026-04-24 00:00:26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_000026"
down_revision = "20260424_000025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("matches_v2") as batch_op:
        batch_op.add_column(sa.Column("compatibility_score", sa.Float(), nullable=False, server_default="0.0"))

    with op.batch_alter_table("matches_v2") as batch_op:
        batch_op.alter_column("compatibility_score", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("matches_v2") as batch_op:
        batch_op.drop_column("compatibility_score")
