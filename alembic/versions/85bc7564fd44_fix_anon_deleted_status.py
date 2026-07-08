"""fix_anon_deleted_status

Revision ID: 85bc7564fd44
Revises: a66f97b65d94
Create Date: 2026-07-08 22:50:54.881310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85bc7564fd44'
down_revision: Union[str, Sequence[str], None] = 'a66f97b65d94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE users SET account_status = 'deleted', is_active = false WHERE user_id = 'ANON_DELETED'")


def downgrade() -> None:
    """Downgrade schema."""
    # No es necesario revertir el centinela a activo, por diseño debe quedar deleted o disabled.
    pass
