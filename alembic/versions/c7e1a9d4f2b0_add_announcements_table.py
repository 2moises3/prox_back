"""Add announcements table

Revision ID: c7e1a9d4f2b0
Revises: b6042994c5b5
Create Date: 2026-06-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e1a9d4f2b0'
down_revision: Union[str, Sequence[str], None] = 'b6042994c5b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'announcements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('placement', sa.String(), nullable=False),
        sa.Column('template_type', sa.String(), nullable=False),
        sa.Column('background_image_url', sa.String(), nullable=True),
        sa.Column('media_public_id', sa.String(), nullable=True),
        sa.Column('cta_text', sa.String(), nullable=True),
        sa.Column('cta_url', sa.String(), nullable=True),
        sa.Column('starts_at', sa.DateTime(), nullable=True),
        sa.Column('ends_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('frequency_cap', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('audience', sa.String(), nullable=False),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_announcements_id'), 'announcements', ['id'], unique=False)
    op.create_index(op.f('ix_announcements_placement'), 'announcements', ['placement'], unique=False)
    op.create_index(op.f('ix_announcements_priority'), 'announcements', ['priority'], unique=False)
    op.create_index(op.f('ix_announcements_is_active'), 'announcements', ['is_active'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_announcements_is_active'), table_name='announcements')
    op.drop_index(op.f('ix_announcements_priority'), table_name='announcements')
    op.drop_index(op.f('ix_announcements_placement'), table_name='announcements')
    op.drop_index(op.f('ix_announcements_id'), table_name='announcements')
    op.drop_table('announcements')
