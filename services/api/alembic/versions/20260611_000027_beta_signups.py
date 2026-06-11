"""beta_signups table

Revision ID: 20260611_000027
Revises: 20260424_000026
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa

revision = "20260611_000027"
down_revision = "20260424_000026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "beta_signups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("source", sa.String(64), nullable=False, server_default="landing_page"),
        sa.Column("city", sa.String(128), nullable=True),
        sa.Column("referral_code", sa.String(64), nullable=True),
        sa.Column("notified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_beta_signups_email", "beta_signups", ["email"])
    op.create_index("ix_beta_signups_created_at", "beta_signups", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_beta_signups_created_at", table_name="beta_signups")
    op.drop_index("ix_beta_signups_email", table_name="beta_signups")
    op.drop_table("beta_signups")
