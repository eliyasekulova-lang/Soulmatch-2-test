"""link psychology reports to assessment sessions

Revision ID: 20260424_000024
Revises: 20260424_000023
Create Date: 2026-04-24 00:00:24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_000024"
down_revision = "20260424_000023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("psycho_reports") as batch_op:
        batch_op.add_column(sa.Column("session_id", sa.String(length=128), nullable=True))
        batch_op.create_foreign_key(
            "fk_psycho_reports_session_id",
            "psycho_assessment_sessions",
            ["session_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_psycho_reports_user_created", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("psycho_reports") as batch_op:
        batch_op.drop_index("ix_psycho_reports_user_created")
        batch_op.drop_constraint("fk_psycho_reports_session_id", type_="foreignkey")
        batch_op.drop_column("session_id")
