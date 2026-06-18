"""merge heads: norm profiles + approval fields

Revision ID: caad02512426
Revises: 0f9e8d7c6b5a, e5f6a7b8c9d0
Create Date: 2026-02-26 21:32:00.059435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'caad02512426'
down_revision: Union[str, Sequence[str], None] = ('0f9e8d7c6b5a', 'e5f6a7b8c9d0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
