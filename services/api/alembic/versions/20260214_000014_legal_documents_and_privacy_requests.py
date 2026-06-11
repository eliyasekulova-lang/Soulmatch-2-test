"""legal docs and privacy requests

Revision ID: 20260214_000014
Revises: 20260214_000013
Create Date: 2026-02-14 00:00:14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260214_000014"
down_revision = "20260214_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("effective_at", sa.DateTime(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "version", name="ux_legal_documents_key_version"),
    )
    op.create_index("ix_legal_documents_key", "legal_documents", ["key"])

    op.create_table(
        "user_consents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("doc_key", sa.String(length=64), nullable=False),
        sa.Column("doc_version", sa.String(length=32), nullable=False),
        sa.Column("consented_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_consents_user_doc", "user_consents", ["user_id", "doc_key", "doc_version"])

    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_check_constraint("ck_privacy_requests_type", "privacy_requests", "type IN ('EXPORT','DELETE','ACCESS','CORRECT')")
    op.create_check_constraint("ck_privacy_requests_status", "privacy_requests", "status IN ('OPEN','IN_PROGRESS','DONE','REJECTED')")
    op.create_index("ix_privacy_requests_user_created", "privacy_requests", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_privacy_requests_user_created", table_name="privacy_requests")
    op.drop_constraint("ck_privacy_requests_status", "privacy_requests", type_="check")
    op.drop_constraint("ck_privacy_requests_type", "privacy_requests", type_="check")
    op.drop_table("privacy_requests")

    op.drop_index("ix_user_consents_user_doc", table_name="user_consents")
    op.drop_table("user_consents")

    op.drop_index("ix_legal_documents_key", table_name="legal_documents")
    op.drop_table("legal_documents")
