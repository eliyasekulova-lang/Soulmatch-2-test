"""phase1 hardening constraints

Revision ID: 20260214_000007
Revises: 20260214_000006
Create Date: 2026-02-14 00:00:07
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260214_000007"
down_revision = "20260214_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint("ck_message_threads_distinct_users", "message_threads", "user_a_id <> user_b_id")
    op.create_check_constraint("ck_messages_non_empty_body", "messages", "length(trim(body)) > 0")
    op.create_check_constraint("ck_billing_products_price_positive", "billing_products", "price_cents > 0")
    op.create_check_constraint(
        "ck_subscriptions_status",
        "subscriptions",
        "status IN ('active', 'canceled', 'expired', 'pending')",
    )
    op.create_check_constraint(
        "ck_payment_events_status",
        "payment_events",
        "status IN ('pending', 'succeeded', 'failed', 'canceled')",
    )
    op.create_index(
        "ux_subscriptions_active_per_user_product",
        "subscriptions",
        ["user_id", "product_code"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("ux_subscriptions_active_per_user_product", table_name="subscriptions")
    op.drop_constraint("ck_payment_events_status", "payment_events", type_="check")
    op.drop_constraint("ck_subscriptions_status", "subscriptions", type_="check")
    op.drop_constraint("ck_billing_products_price_positive", "billing_products", type_="check")
    op.drop_constraint("ck_messages_non_empty_body", "messages", type_="check")
    op.drop_constraint("ck_message_threads_distinct_users", "message_threads", type_="check")
