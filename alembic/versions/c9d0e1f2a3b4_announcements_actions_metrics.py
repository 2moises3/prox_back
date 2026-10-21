"""announcements_actions_metrics

Anuncios: destino objetivo (para el detalle de destino) y métricas de vistas, clics y cierres.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-18 23:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("announcements")}
    if "target_destination_id" not in existing:
        op.add_column("announcements", sa.Column("target_destination_id", sa.String(), nullable=True))
        op.create_foreign_key(
            "fk_announcements_target_destination", "announcements", "destinations",
            ["target_destination_id"], ["destination_id"], ondelete="SET NULL",
        )
    for name in ("impressions", "clicks", "dismissals"):
        if name not in existing:
            op.add_column("announcements", sa.Column(name, sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    for name in ("dismissals", "clicks", "impressions"):
        op.drop_column("announcements", name)
    op.drop_constraint("fk_announcements_target_destination", "announcements", type_="foreignkey")
    op.drop_column("announcements", "target_destination_id")
