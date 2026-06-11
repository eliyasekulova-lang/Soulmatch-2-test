"""db hardening indexes and constraints

Revision ID: 20260214_000005
Revises: 20260213_000004
Create Date: 2026-02-14 00:00:05
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260214_000005"
down_revision = "20260213_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.create_index("ix_astro_vectors_schema_version", "astro_vectors", ["schema_version"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"])
    op.create_index("ix_consent_records_user_accepted_at", "consent_records", ["user_id", "accepted_at"])
    op.create_check_constraint(
        "ck_match_results_mode",
        "match_results",
        "mode IN ('romance', 'friendship')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_match_results_mode", "match_results", type_="check")
    op.drop_index("ix_consent_records_user_accepted_at", table_name="consent_records")
    op.drop_index("ix_analytics_events_created_at", table_name="analytics_events")
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_index("ix_astro_vectors_schema_version", table_name="astro_vectors")
    op.drop_index("ix_users_created_at", table_name="users")
