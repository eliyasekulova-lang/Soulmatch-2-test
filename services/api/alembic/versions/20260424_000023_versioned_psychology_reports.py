"""allow versioned psychology reports

Revision ID: 20260424_000023
Revises: 20260424_000022
Create Date: 2026-04-24 00:00:23
"""

from alembic import op


revision = "20260424_000023"
down_revision = "20260424_000022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("psycho_reports") as batch_op:
        batch_op.drop_constraint("uq_psycho_reports_user_id", type_="unique")


def downgrade() -> None:
    with op.batch_alter_table("psycho_reports") as batch_op:
        batch_op.create_unique_constraint("uq_psycho_reports_user_id", ["user_id"])
