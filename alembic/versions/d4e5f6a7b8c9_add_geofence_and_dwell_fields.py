"""Add geofence and dwell fields to tourism_catalog and visits

Revision ID: d4e5f6a7b8c9
Revises: b3d5e7f9a1c2
Create Date: 2026-10-26 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'b3d5e7f9a1c2'
branch_labels = None
depends_on = None


def upgrade():
    # Columnas en tourism_catalog
    with op.batch_alter_table('tourism_catalog') as batch_op:
        batch_op.add_column(sa.Column('geofence_radius_meters', sa.Integer(), nullable=True, server_default='250'))
        batch_op.add_column(sa.Column('min_dwell_minutes', sa.Integer(), nullable=True, server_default='20'))

    # Columnas en visits
    with op.batch_alter_table('visits') as batch_op:
        batch_op.add_column(sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('dwell_minutes', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('entry_latitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('entry_longitude', sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table('visits') as batch_op:
        batch_op.drop_column('entry_longitude')
        batch_op.drop_column('entry_latitude')
        batch_op.drop_column('dwell_minutes')
        batch_op.drop_column('completed_at')
        batch_op.drop_column('started_at')

    with op.batch_alter_table('tourism_catalog') as batch_op:
        batch_op.drop_column('min_dwell_minutes')
        batch_op.drop_column('geofence_radius_meters')
