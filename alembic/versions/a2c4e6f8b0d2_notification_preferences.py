"""Account preferences for the in-app notification centre.

Revision ID: a2c4e6f8b0d2
Revises: e1f2a3b4c5d6
"""
from alembic import op
import sqlalchemy as sa

revision = "a2c4e6f8b0d2"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("recommendations", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("new_destinations", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("announcements", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade():
    op.drop_table("notification_preferences")
