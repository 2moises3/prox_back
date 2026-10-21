"""notifications

Centro de notificaciones: avisos personales y lecturas de anuncios.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-16 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    if not insp.has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("route", sa.String(), nullable=True),
            sa.Column("destination_id", sa.String(), nullable=True),
            sa.Column("dedupe_key", sa.String(), nullable=True),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "dedupe_key", name="uq_notification_user_key"),
        )
        op.create_index("ix_notifications_id", "notifications", ["id"])
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
        op.create_index("ix_notifications_kind", "notifications", ["kind"])

    if not insp.has_table("announcement_reads"):
        op.create_table(
            "announcement_reads",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("announcement_id", sa.Integer(), sa.ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False),
            sa.Column("read_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "announcement_id", name="uq_announcement_read"),
        )
        op.create_index("ix_announcement_reads_id", "announcement_reads", ["id"])
        op.create_index("ix_announcement_reads_user_id", "announcement_reads", ["user_id"])
        op.create_index("ix_announcement_reads_announcement_id", "announcement_reads", ["announcement_id"])


def downgrade() -> None:
    op.drop_table("announcement_reads")
    op.drop_table("notifications")
