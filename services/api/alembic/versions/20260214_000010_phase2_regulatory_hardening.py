"""phase2 regulatory hardening

Revision ID: 20260214_000010
Revises: 20260214_000009
Create Date: 2026-02-14 00:00:10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260214_000010"
down_revision = "20260214_000009"
branch_labels = None
depends_on = None


POLICY_UNIQUE_OLD = "ux_policy_documents_identity"
POLICY_UNIQUE_NEW = "ux_policy_documents_identity_v2"


def upgrade() -> None:
    op.add_column("policy_documents", sa.Column("jurisdiction", sa.String(length=16), nullable=False, server_default="GLOBAL"))
    op.add_column("policy_documents", sa.Column("platform", sa.String(length=16), nullable=False, server_default="all"))
    op.add_column("policy_documents", sa.Column("legal_basis", sa.String(length=64), nullable=False, server_default="contract"))
    op.add_column("policy_documents", sa.Column("attorney_review_required", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")))
    op.add_column("policy_documents", sa.Column("attorney_approved_at", sa.DateTime(), nullable=True))
    op.add_column("policy_documents", sa.Column("attorney_approved_by", sa.String(length=255), nullable=True))

    op.drop_constraint(POLICY_UNIQUE_OLD, "policy_documents", type_="unique")
    op.create_unique_constraint(
        POLICY_UNIQUE_NEW,
        "policy_documents",
        ["policy_id", "version", "locale", "jurisdiction", "platform"],
    )
    op.create_index(
        "ix_policy_documents_lookup_v2",
        "policy_documents",
        ["policy_id", "locale", "jurisdiction", "platform", "published_at"],
    )

    op.add_column("consent_events", sa.Column("jurisdiction", sa.String(length=16), nullable=True))
    op.add_column("consent_events", sa.Column("platform", sa.String(length=16), nullable=True))
    op.add_column("consent_events", sa.Column("legal_basis", sa.String(length=64), nullable=True))

    op.add_column("user_policy_acceptance", sa.Column("locale", sa.String(length=16), nullable=False, server_default="en-CA"))
    op.add_column("user_policy_acceptance", sa.Column("jurisdiction", sa.String(length=16), nullable=False, server_default="GLOBAL"))
    op.add_column("user_policy_acceptance", sa.Column("platform", sa.String(length=16), nullable=False, server_default="all"))
    op.add_column("user_policy_acceptance", sa.Column("accepted_ip", sa.String(length=64), nullable=True))
    op.add_column("user_policy_acceptance", sa.Column("user_agent", sa.String(length=512), nullable=True))
    op.add_column("user_policy_acceptance", sa.Column("app_version", sa.String(length=32), nullable=True))
    op.add_column("user_policy_acceptance", sa.Column("accepted_policy_hash", sa.String(length=128), nullable=True))

    op.add_column("user_rights_requests", sa.Column("locale", sa.String(length=16), nullable=True))
    op.add_column("user_rights_requests", sa.Column("jurisdiction", sa.String(length=16), nullable=True))

    op.add_column("moderation_reports", sa.Column("severity", sa.String(length=16), nullable=False, server_default="standard"))
    op.add_column("moderation_reports", sa.Column("escalation_status", sa.String(length=32), nullable=False, server_default="none"))
    op.add_column("moderation_reports", sa.Column("escalated_at", sa.DateTime(), nullable=True))
    op.add_column("moderation_reports", sa.Column("escalation_runbook_ref", sa.String(length=128), nullable=True))

    op.add_column("audit_logs", sa.Column("evidence_ref", sa.String(length=255), nullable=True))

    op.add_column("retention_rules", sa.Column("purge_mode", sa.String(length=32), nullable=False, server_default="hard_delete"))
    op.add_column("retention_rules", sa.Column("applies_to_backups", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")))

    op.add_column("vendor_processors", sa.Column("subprocessor_country", sa.String(length=32), nullable=True))
    op.add_column("vendor_processors", sa.Column("data_transfer_region", sa.String(length=32), nullable=True))
    op.add_column("vendor_processors", sa.Column("scc_reference", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("vendor_processors", "scc_reference")
    op.drop_column("vendor_processors", "data_transfer_region")
    op.drop_column("vendor_processors", "subprocessor_country")

    op.drop_column("retention_rules", "applies_to_backups")
    op.drop_column("retention_rules", "purge_mode")

    op.drop_column("audit_logs", "evidence_ref")

    op.drop_column("moderation_reports", "escalation_runbook_ref")
    op.drop_column("moderation_reports", "escalated_at")
    op.drop_column("moderation_reports", "escalation_status")
    op.drop_column("moderation_reports", "severity")

    op.drop_column("user_rights_requests", "jurisdiction")
    op.drop_column("user_rights_requests", "locale")

    op.drop_column("user_policy_acceptance", "accepted_policy_hash")
    op.drop_column("user_policy_acceptance", "app_version")
    op.drop_column("user_policy_acceptance", "user_agent")
    op.drop_column("user_policy_acceptance", "accepted_ip")
    op.drop_column("user_policy_acceptance", "platform")
    op.drop_column("user_policy_acceptance", "jurisdiction")
    op.drop_column("user_policy_acceptance", "locale")

    op.drop_column("consent_events", "legal_basis")
    op.drop_column("consent_events", "platform")
    op.drop_column("consent_events", "jurisdiction")

    op.drop_index("ix_policy_documents_lookup_v2", table_name="policy_documents")
    op.drop_constraint(POLICY_UNIQUE_NEW, "policy_documents", type_="unique")
    op.create_unique_constraint(POLICY_UNIQUE_OLD, "policy_documents", ["policy_id", "version", "locale"])

    op.drop_column("policy_documents", "attorney_approved_by")
    op.drop_column("policy_documents", "attorney_approved_at")
    op.drop_column("policy_documents", "attorney_review_required")
    op.drop_column("policy_documents", "legal_basis")
    op.drop_column("policy_documents", "platform")
    op.drop_column("policy_documents", "jurisdiction")
