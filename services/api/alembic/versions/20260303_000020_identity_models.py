"""identity model layers, eligibility state, and compatibility matches

Revision ID: 20260303_000020
Revises: 20260219_000019
Create Date: 2026-03-03 00:00:20
"""

from alembic import op

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260303_000020"
down_revision = "20260219_000019"
branch_labels = None
depends_on = None


PROFILE_STAGE = postgresql.ENUM("incomplete", "calibrating", "eligible", name="profile_stage", create_type=False)



def upgrade() -> None:
    PROFILE_STAGE.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_profile_state",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("stage", PROFILE_STAGE, nullable=False, server_default="incomplete"),
        sa.Column("astro_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("psycho_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("required_modules_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("quality_pass", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("astro_completion", sa.Float(), nullable=False, server_default="0"),
        sa.Column("psycho_completion", sa.Float(), nullable=False, server_default="0"),
        sa.Column("behavior_completion", sa.Float(), nullable=False, server_default="0"),
        sa.Column("astro_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("psycho_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("behavior_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("overall_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "birth_data",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("birth_time", sa.Time(), nullable=False),
        sa.Column("birth_place_name", sa.Text(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("timezone_iana", sa.String(length=128), nullable=False),
        sa.Column("birth_datetime_utc", sa.DateTime(), nullable=False),
        sa.Column("dst_flag", sa.Boolean(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "natal_chart",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("asc_sign", sa.SmallInteger(), nullable=False),
        sa.Column("asc_deg", sa.Float(), nullable=False),
        sa.Column("planets", sa.JSON(), nullable=False),
        sa.Column("aspects", sa.JSON(), nullable=False),
        sa.Column("astro_features", sa.JSON(), nullable=False),
        sa.Column("astro_vector", sa.JSON(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "psycho_items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("reverse_key", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("trait_key", sa.String(length=64), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_psycho_items_module", "psycho_items", ["module"])

    op.create_table(
        "psycho_responses",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("answer", sa.SmallInteger(), nullable=False),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["psycho_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "item_id"),
    )
    op.create_index("ix_psycho_responses_user", "psycho_responses", ["user_id"])

    op.create_table(
        "psycho_scores",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("o", sa.Float(), nullable=False),
        sa.Column("c", sa.Float(), nullable=False),
        sa.Column("e", sa.Float(), nullable=False),
        sa.Column("a", sa.Float(), nullable=False),
        sa.Column("n", sa.Float(), nullable=False),
        sa.Column("att_anxiety", sa.Float(), nullable=False),
        sa.Column("att_avoid", sa.Float(), nullable=False),
        sa.Column("conflict_direct", sa.Float(), nullable=False),
        sa.Column("conflict_avoid", sa.Float(), nullable=False),
        sa.Column("conflict_delay", sa.Float(), nullable=False),
        sa.Column("value_stability", sa.Float(), nullable=False),
        sa.Column("value_novelty", sa.Float(), nullable=False),
        sa.Column("aff_attention", sa.Float(), nullable=False),
        sa.Column("psycho_vector", sa.JSON(), nullable=False),
        sa.Column("psycho_uncertainty", sa.JSON(), nullable=False),
        sa.Column("quality_flags", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "behavior_features",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("response_consistency", sa.Float(), nullable=False, server_default="0"),
        sa.Column("response_delay_var", sa.Float(), nullable=False, server_default="0"),
        sa.Column("initiative_ratio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("conversation_balance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("engagement_stability", sa.Float(), nullable=False, server_default="0"),
        sa.Column("boundary_respect", sa.Float(), nullable=False, server_default="0"),
        sa.Column("emotional_variability", sa.Float(), nullable=False, server_default="0"),
        sa.Column("behavior_vector", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("behavior_uncertainty", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "matches_v2",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("other_user_id", sa.String(length=128), nullable=False),
        sa.Column("psycho_score", sa.Float(), nullable=False),
        sa.Column("astro_score", sa.Float(), nullable=False),
        sa.Column("behavior_score", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["other_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "other_user_id"),
    )
    op.create_index("ix_matches_v2_user_final", "matches_v2", ["user_id", "final_score"])


def downgrade() -> None:
    op.drop_index("ix_matches_v2_user_final", table_name="matches_v2")
    op.drop_table("matches_v2")

    op.drop_table("behavior_features")
    op.drop_table("psycho_scores")

    op.drop_index("ix_psycho_responses_user", table_name="psycho_responses")
    op.drop_table("psycho_responses")

    op.drop_index("ix_psycho_items_module", table_name="psycho_items")
    op.drop_table("psycho_items")

    op.drop_table("natal_chart")
    op.drop_table("birth_data")
    op.drop_table("user_profile_state")

    PROFILE_STAGE.drop(op.get_bind(), checkfirst=True)
