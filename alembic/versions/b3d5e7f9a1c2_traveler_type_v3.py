"""Tipo de viajero explícito, sin inferencia ni reasignación de perfiles existentes."""
from alembic import op
import sqlalchemy as sa
revision = 'b3d5e7f9a1c2'
down_revision = 'a2c4e6f8b0d2'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('traveler_profiles', sa.Column('perfil_turistico', sa.String(), nullable=True))

def downgrade():
    op.drop_column('traveler_profiles', 'perfil_turistico')
