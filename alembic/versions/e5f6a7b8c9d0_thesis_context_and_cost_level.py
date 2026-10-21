"""thesis_context_and_cost_level

- destination_month_context: explicaciones y riesgos de la tesis (Fase 4) y visitantes medios.
- tourism_catalog.cost_level: nivel de costo estimado (bajo/medio/alto), dato editorial.

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
Create Date: 2026-10-16 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add(table: str, column: sa.Column) -> None:
    insp = sa.inspect(op.get_bind())
    if column.name not in {c["name"] for c in insp.get_columns(table)}:
        op.add_column(table, column)


def upgrade() -> None:
    _add("destination_month_context", sa.Column("clima_explicacion", sa.Text(), nullable=True))
    _add("destination_month_context", sa.Column("clima_riesgo", sa.String(), nullable=True))
    _add("destination_month_context", sa.Column("aforo_explicacion", sa.Text(), nullable=True))
    _add("destination_month_context", sa.Column("visitantes_medios", sa.Float(), nullable=True))
    _add("tourism_catalog", sa.Column("cost_level", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("tourism_catalog", "cost_level")
    op.drop_column("destination_month_context", "visitantes_medios")
    op.drop_column("destination_month_context", "aforo_explicacion")
    op.drop_column("destination_month_context", "clima_riesgo")
    op.drop_column("destination_month_context", "clima_explicacion")
