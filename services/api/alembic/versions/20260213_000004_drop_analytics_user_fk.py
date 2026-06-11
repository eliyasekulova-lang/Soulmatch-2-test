"""drop analytics user foreign key

Revision ID: 20260213_000004
Revises: 20260213_000003
Create Date: 2026-02-13 00:00:04
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260213_000004"
down_revision = "20260213_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'analytics_events_user_id_fkey'
              ) THEN
                ALTER TABLE analytics_events DROP CONSTRAINT analytics_events_user_id_fkey;
              END IF;
            END$$;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'analytics_events_user_id_fkey'
              ) THEN
                ALTER TABLE analytics_events
                ADD CONSTRAINT analytics_events_user_id_fkey
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
              END IF;
            END$$;
            """
        )
    )
