"""reset_derived_profile_weights

Los pesos peso_* de los perfiles los inventaba el backend al guardar el perfil (la app no tiene
deslizadores). Como no eran iguales, el motor los tomaba como elección del viajero y no aplicaba
los pesos por tipo de viajero de la tesis. Se dejan todos en 3.0 (neutro) para que el motor infiera.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-10-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PESOS = (
    "peso_accesibilidad", "peso_aforo_multitudes", "peso_alojamiento", "peso_atencion_servicio",
    "peso_atractivos", "peso_clima", "peso_costos", "peso_gastronomia", "peso_limpieza", "peso_seguridad",
)


def upgrade() -> None:
    op.execute("UPDATE traveler_profiles SET " + ", ".join(f"{p} = 3.0" for p in PESOS))


def downgrade() -> None:
    # Los pesos derivados no se pueden reconstruir; no hay nada que deshacer.
    pass
