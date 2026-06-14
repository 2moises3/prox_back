"""add_dias_viaje_tipo_interes_intereses

Revision ID: eba1b0c8f8fd
Revises: f3c559b1fe02
Create Date: 2026-06-14 03:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eba1b0c8f8fd'
down_revision: Union[str, None] = 'f3c559b1fe02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('traveler_profiles', sa.Column('dias_viaje', sa.Integer(), nullable=True))
    op.add_column('traveler_profiles', sa.Column('tipo_interes', sa.String(), nullable=True))
    op.add_column('traveler_profiles', sa.Column('intereses', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('traveler_profiles', 'intereses')
    op.drop_column('traveler_profiles', 'tipo_interes')
    op.drop_column('traveler_profiles', 'dias_viaje')
