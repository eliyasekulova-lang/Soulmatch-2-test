"""legal compliance hooks

Revision ID: 20260214_000013
Revises: 20260214_000012
Create Date: 2026-02-14 00:00:13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260214_000013"
down_revision = "20260214_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_consents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("receipt_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("consent_timestamp", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_id"),
    )
    op.create_index("ix_legal_consents_email_time", "legal_consents", ["email", "consent_timestamp"])


def downgrade() -> None:
    op.drop_index("ix_legal_consents_email_time", table_name="legal_consents")
    op.drop_table("legal_consents")
