"""phase2 security compliance extensions

Revision ID: 20260214_000009
Revises: 20260214_000008
Create Date: 2026-02-14 00:00:09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260214_000009"
down_revision = "20260214_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("birth_date_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("birth_time_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("birth_place_encrypted", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("locale", sa.String(length=16), nullable=False, server_default="en-CA"))
    op.add_column("users", sa.Column("jurisdiction", sa.String(length=16), nullable=False, server_default="CA"))
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    op.create_table(
        "retention_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("data_class", sa.String(length=64), nullable=False),
        sa.Column("ttl_days", sa.Integer(), nullable=False),
        sa.Column("legal_hold_allowed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("data_class"),
    )
    op.create_table(
        "vendor_processors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("data_categories", sa.JSON(), nullable=False),
        sa.Column("transfer_mechanism", sa.String(length=64), nullable=True),
        sa.Column("dpa_url", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "incident_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("notified_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "law_enforcement_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_reference", sa.String(length=128), nullable=False),
        sa.Column("jurisdiction", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_reference"),
    )

    op.create_check_constraint(
        "ck_deletion_queue_scope",
        "deletion_queue",
        "scope IN ('database', 'file_storage', 'backups', 'search_indexes', 'analytics', 'export_bundle')",
    )
    op.create_check_constraint(
        "ck_user_rights_requests_type",
        "user_rights_requests",
        "right_type IN ('export', 'delete', 'correct', 'restrict_processing', 'withdraw_consent')",
    )

    op.execute(
        """
        INSERT INTO retention_rules (data_class, ttl_days, legal_hold_allowed, created_at)
        VALUES
          ('messages', 1095, TRUE, NOW()),
          ('audit_logs', 2555, TRUE, NOW()),
          ('rights_exports', 7, FALSE, NOW()),
          ('temp_media_uploads', 2, FALSE, NOW())
        ON CONFLICT (data_class) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM retention_rules WHERE data_class IN ('messages','audit_logs','rights_exports','temp_media_uploads')")
    op.drop_constraint("ck_user_rights_requests_type", "user_rights_requests", type_="check")
    op.drop_constraint("ck_deletion_queue_scope", "deletion_queue", type_="check")
    op.drop_table("law_enforcement_requests")
    op.drop_table("incident_reports")
    op.drop_table("vendor_processors")
    op.drop_table("retention_rules")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "jurisdiction")
    op.drop_column("users", "locale")
    op.drop_column("users", "birth_place_encrypted")
    op.drop_column("users", "birth_time_encrypted")
    op.drop_column("users", "birth_date_encrypted")
