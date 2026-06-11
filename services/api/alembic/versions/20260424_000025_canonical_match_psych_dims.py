"""expand canonical psych dims and stabilize match dynamics storage

Revision ID: 20260424_000025
Revises: 20260424_000024
Create Date: 2026-04-24 00:00:25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260424_000025"
down_revision = "20260424_000024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("psycho_scores") as batch_op:
        batch_op.add_column(sa.Column("reassurance_need", sa.Float(), nullable=False, server_default="0.5"))
        batch_op.add_column(sa.Column("independence_need", sa.Float(), nullable=False, server_default="0.5"))
        batch_op.add_column(sa.Column("vulnerability_comfort", sa.Float(), nullable=False, server_default="0.5"))
        batch_op.add_column(sa.Column("emotional_regulation", sa.Float(), nullable=False, server_default="0.5"))
        batch_op.add_column(sa.Column("aff_touch", sa.Float(), nullable=False, server_default="0.5"))
        batch_op.add_column(sa.Column("aff_words", sa.Float(), nullable=False, server_default="0.5"))
        batch_op.add_column(sa.Column("aff_acts", sa.Float(), nullable=False, server_default="0.5"))
        batch_op.add_column(sa.Column("aff_gifts", sa.Float(), nullable=False, server_default="0.5"))

    with op.batch_alter_table("matches_v2") as batch_op:
        batch_op.add_column(sa.Column("dynamics_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

    with op.batch_alter_table("psycho_scores") as batch_op:
        batch_op.alter_column("reassurance_need", server_default=None)
        batch_op.alter_column("independence_need", server_default=None)
        batch_op.alter_column("vulnerability_comfort", server_default=None)
        batch_op.alter_column("emotional_regulation", server_default=None)
        batch_op.alter_column("aff_touch", server_default=None)
        batch_op.alter_column("aff_words", server_default=None)
        batch_op.alter_column("aff_acts", server_default=None)
        batch_op.alter_column("aff_gifts", server_default=None)

    with op.batch_alter_table("matches_v2") as batch_op:
        batch_op.alter_column("dynamics_payload", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("matches_v2") as batch_op:
        batch_op.drop_column("dynamics_payload")

    with op.batch_alter_table("psycho_scores") as batch_op:
        batch_op.drop_column("aff_gifts")
        batch_op.drop_column("aff_acts")
        batch_op.drop_column("aff_words")
        batch_op.drop_column("aff_touch")
        batch_op.drop_column("emotional_regulation")
        batch_op.drop_column("vulnerability_comfort")
        batch_op.drop_column("independence_need")
        batch_op.drop_column("reassurance_need")
