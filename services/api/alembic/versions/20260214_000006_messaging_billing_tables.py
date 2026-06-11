"""messaging and billing tables

Revision ID: 20260214_000006
Revises: 20260214_000005
Create Date: 2026-02-14 00:00:06
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260214_000006"
down_revision = "20260214_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_threads",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("pair_key", sa.String(length=300), nullable=False),
        sa.Column("user_a_id", sa.String(length=128), nullable=False),
        sa.Column("user_b_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_a_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_b_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pair_key"),
    )
    op.create_index("ix_message_threads_user_a_id", "message_threads", ["user_a_id"])
    op.create_index("ix_message_threads_user_b_id", "message_threads", ["user_b_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("sender_user_id", sa.String(length=128), nullable=False),
        sa.Column("recipient_user_id", sa.String(length=128), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["message_threads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_thread_created", "messages", ["thread_id", "created_at"])

    op.create_table(
        "billing_products",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("product_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_code"], ["billing_products.code"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_user_status", "subscriptions", ["user_id", "status"])

    op.create_table(
        "payment_events",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("product_code", sa.String(length=64), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_event_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_code"], ["billing_products.code"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_events_user_created", "payment_events", ["user_id", "created_at"])
    op.create_index("ix_payment_events_provider_event_id", "payment_events", ["provider_event_id"], unique=True)

    op.execute(
        """
        INSERT INTO billing_products (code, name, price_cents, currency, is_active, created_at)
        VALUES
          ('premium_monthly', 'Premium Monthly', 1499, 'USD', TRUE, NOW()),
          ('synastry_report', 'One-Off Synastry Report', 999, 'USD', TRUE, NOW())
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_payment_events_provider_event_id", table_name="payment_events")
    op.drop_index("ix_payment_events_user_created", table_name="payment_events")
    op.drop_table("payment_events")
    op.drop_index("ix_subscriptions_user_status", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_table("billing_products")
    op.drop_index("ix_messages_thread_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_message_threads_user_b_id", table_name="message_threads")
    op.drop_index("ix_message_threads_user_a_id", table_name="message_threads")
    op.drop_table("message_threads")
