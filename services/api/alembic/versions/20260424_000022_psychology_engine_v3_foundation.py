"""psychology engine v3 foundation tables

Revision ID: 20260424_000022
Revises: 20260303_000021
Create Date: 2026-04-24 00:00:22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_000022"
down_revision = "20260303_000021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "psycho_assessment_sessions",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("assessment_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("device_type", sa.String(length=32), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "psycho_item_responses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("answer_value", sa.Integer(), nullable=True),
        sa.Column("first_answer_value", sa.Integer(), nullable=True),
        sa.Column("final_answer_value", sa.Integer(), nullable=True),
        sa.Column("considered_answer_value", sa.Integer(), nullable=True),
        sa.Column("changed_answer_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("skipped", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("returned_to_question", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("uncertainty_reason", sa.String(length=255), nullable=True),
        sa.Column("free_text_note", sa.Text(), nullable=True),
        sa.Column("device_type", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["psycho_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["psycho_assessment_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "psycho_derived_patterns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("pattern_key", sa.String(length=64), nullable=False),
        sa.Column("pattern_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("contributing_dimensions", sa.JSON(), nullable=False),
        sa.Column("explanation_internal", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "psycho_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("report_version", sa.String(length=32), nullable=False),
        sa.Column("personality_summary", sa.Text(), nullable=False),
        sa.Column("relationship_style", sa.Text(), nullable=False),
        sa.Column("conflict_style", sa.Text(), nullable=False),
        sa.Column("attachment_style", sa.Text(), nullable=False),
        sa.Column("affection_needs", sa.Text(), nullable=False),
        sa.Column("blind_spots", sa.Text(), nullable=False),
        sa.Column("best_match_type", sa.Text(), nullable=False),
        sa.Column("growth_suggestions", sa.Text(), nullable=False),
        sa.Column("confidence_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_psycho_reports_user_id"),
    )

    op.add_column(
        "psycho_items",
        sa.Column("item_type", sa.String(length=32), nullable=False, server_default="likert"),
    )
    op.add_column(
        "psycho_items",
        sa.Column("version", sa.String(length=32), nullable=False, server_default="v1"),
    )
    op.add_column(
        "psycho_items",
        sa.Column("dimension_group", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "psycho_items",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "psycho_items",
        sa.Column("followup_eligible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.execute("UPDATE psycho_items SET item_type = 'likert' WHERE item_type IS NULL")
    op.execute("UPDATE psycho_items SET version = 'v1' WHERE version IS NULL")
    op.execute("UPDATE psycho_items SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE psycho_items SET followup_eligible = false WHERE followup_eligible IS NULL")

    op.alter_column("psycho_items", "item_type", server_default=None)
    op.alter_column("psycho_items", "version", server_default=None)
    op.alter_column("psycho_items", "is_active", server_default=None)
    op.alter_column("psycho_items", "followup_eligible", server_default=None)
    op.alter_column("psycho_item_responses", "changed_answer_count", server_default=None)
    op.alter_column("psycho_item_responses", "skipped", server_default=None)
    op.alter_column("psycho_item_responses", "returned_to_question", server_default=None)


def downgrade() -> None:
    op.drop_column("psycho_items", "followup_eligible")
    op.drop_column("psycho_items", "is_active")
    op.drop_column("psycho_items", "dimension_group")
    op.drop_column("psycho_items", "version")
    op.drop_column("psycho_items", "item_type")

    op.drop_table("psycho_reports")
    op.drop_table("psycho_derived_patterns")
    op.drop_table("psycho_item_responses")
    op.drop_table("psycho_assessment_sessions")
