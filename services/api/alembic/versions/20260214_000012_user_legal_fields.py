"""user legal profile fields

Revision ID: 20260214_000012
Revises: 20260214_000011
Create Date: 2026-02-14 00:00:12
"""

from alembic import op
import sqlalchemy as sa


revision = "20260214_000012"
down_revision = "20260214_000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("legal_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("birth_city", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("birth_country", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("status", sa.String(length=32), nullable=False, server_default="active"))

    op.execute("UPDATE users SET legal_name = name WHERE legal_name IS NULL")
    op.execute("UPDATE users SET birth_city = birth_place WHERE birth_city IS NULL")
    op.execute("UPDATE users SET birth_country = 'Unknown' WHERE birth_country IS NULL")


def downgrade() -> None:
    op.drop_column("users", "status")
    op.drop_column("users", "birth_country")
    op.drop_column("users", "birth_city")
    op.drop_column("users", "legal_name")
