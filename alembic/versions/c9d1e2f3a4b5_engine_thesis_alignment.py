"""engine_thesis_alignment

- destinations.in_engine: participación explícita en el motor (separada de is_active).
- engine_config.alpha_absa: peso ABSA de la afinidad (tesis Fase 3 = 0.25).
- destination_month_context.clima_por_preferencia / aforo_por_tolerancia (JSON).
- Crea archives y app_releases si no existen (la migración 2e33ce25ac8e de
  archives quedó vacía y en algunas BD app_releases nunca se creó).

Idempotente: cada paso revisa el estado real de la BD antes de actuar.

Revision ID: c9d1e2f3a4b5
Revises: b4f8d9a2e7c1
Create Date: 2026-10-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9d1e2f3a4b5'
down_revision: Union[str, Sequence[str], None] = 'b4f8d9a2e7c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table: str, column: str) -> bool:
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # --- tablas que faltaban (se crean desde el modelo vigente) ---
    from app.models.base import Base
    import app.models  # noqa: F401  (registra todos los modelos)

    for name in ("archives", "app_releases"):
        if not insp.has_table(name):
            Base.metadata.tables[name].create(bind)

    insp = sa.inspect(bind)

    # --- destinations.in_engine ---
    if not _has_column(insp, "destinations", "in_engine"):
        op.add_column(
            "destinations",
            sa.Column("in_engine", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

    # --- engine_config.alpha_absa ---
    if not _has_column(insp, "engine_config", "alpha_absa"):
        op.add_column(
            "engine_config",
            sa.Column("alpha_absa", sa.Float(), nullable=False, server_default="0.25"),
        )

    # --- destination_month_context: señales personalizadas ---
    if not _has_column(insp, "destination_month_context", "clima_por_preferencia"):
        op.add_column("destination_month_context", sa.Column("clima_por_preferencia", sa.JSON(), nullable=True))
    if not _has_column(insp, "destination_month_context", "aforo_por_tolerancia"):
        op.add_column("destination_month_context", sa.Column("aforo_por_tolerancia", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Las tablas archives/app_releases no se eliminan: pueden contener datos.
    op.drop_column("destination_month_context", "aforo_por_tolerancia")
    op.drop_column("destination_month_context", "clima_por_preferencia")
    op.drop_column("engine_config", "alpha_absa")
    op.drop_column("destinations", "in_engine")
