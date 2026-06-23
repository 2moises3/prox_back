"""Add engine V1 tables (engine_config, destination_tags, destination_month_context)

Revision ID: a1b2c3d4e5f6
Revises: f3c4d5e6a7b8
Create Date: 2026-06-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3c4d5e6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ── engine_config ──
    op.create_table(
        'engine_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alpha_afinidad', sa.Float(), nullable=True),
        sa.Column('beta_intereses', sa.Float(), nullable=True),
        sa.Column('beta_contexto', sa.Float(), nullable=True),
        sa.Column('w_clima', sa.Float(), nullable=True),
        sa.Column('w_aforo', sa.Float(), nullable=True),
        sa.Column('factor_tolerancia_baja', sa.Float(), nullable=True),
        sa.Column('factor_tolerancia_media', sa.Float(), nullable=True),
        sa.Column('factor_tolerancia_alta', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_engine_config_id'), 'engine_config', ['id'])

    # ── destination_tags ──
    op.create_table(
        'destination_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('destination_id', sa.String(), nullable=False),
        sa.Column('tag', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['destination_id'], ['destinations.destination_id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_destination_tags_id'), 'destination_tags', ['id'])
    op.create_index(op.f('ix_destination_tags_destination_id'), 'destination_tags', ['destination_id'])
    op.create_index(op.f('ix_destination_tags_tag'), 'destination_tags', ['tag'])

    # ── destination_month_context ──
    op.create_table(
        'destination_month_context',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('destination_id', sa.String(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('clima_score', sa.Float(), nullable=True),
        sa.Column('clima_nivel', sa.String(), nullable=True),
        sa.Column('temp_prom', sa.Float(), nullable=True),
        sa.Column('pp', sa.Float(), nullable=True),
        sa.Column('aforo_score', sa.Float(), nullable=True),
        sa.Column('aforo_nivel', sa.String(), nullable=True),
        sa.Column('aforo_fuente', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['destination_id'], ['destinations.destination_id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('destination_id', 'month', name='uq_dest_month'),
    )
    op.create_index(op.f('ix_destination_month_context_id'), 'destination_month_context', ['id'])
    op.create_index(op.f('ix_destination_month_context_destination_id'), 'destination_month_context', ['destination_id'])
    op.create_index(op.f('ix_destination_month_context_month'), 'destination_month_context', ['month'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('destination_month_context')
    op.drop_table('destination_tags')
    op.drop_table('engine_config')
