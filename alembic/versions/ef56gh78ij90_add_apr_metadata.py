"""add apr metadata fields

Revision ID: ef56gh78ij90
Revises: cd34ef56gh78
Create Date: 2026-01-23 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ef56gh78ij90"
down_revision: Union[str, Sequence[str], None] = "cd34ef56gh78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("aprs") as batch_op:
        batch_op.add_column(sa.Column("source_hashes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("template_version", sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("aprs") as batch_op:
        batch_op.drop_column("template_version")
        batch_op.drop_column("source_hashes")
