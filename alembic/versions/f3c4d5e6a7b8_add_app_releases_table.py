"""Add app_releases table

Revision ID: f3c4d5e6a7b8
Revises: e2b3c4d5f6a7
Create Date: 2026-06-16 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3c4d5e6a7b8'
down_revision: Union[str, Sequence[str], None] = 'e2b3c4d5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'app_releases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version_name', sa.String(), nullable=False),
        sa.Column('version_code', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False, server_default='android'),
        sa.Column('apk_url', sa.String(), nullable=True),
        sa.Column('file_public_id', sa.String(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_app_releases_id'), 'app_releases', ['id'], unique=False)
    op.create_index(op.f('ix_app_releases_platform'), 'app_releases', ['platform'], unique=False)
    op.create_index(op.f('ix_app_releases_is_published'), 'app_releases', ['is_published'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_app_releases_is_published'), table_name='app_releases')
    op.drop_index(op.f('ix_app_releases_platform'), table_name='app_releases')
    op.drop_index(op.f('ix_app_releases_id'), table_name='app_releases')
    op.drop_table('app_releases')
