"""add apr shares

Revision ID: cd34ef56gh78
Revises: ab12cd34ef56
Create Date: 2026-01-23 13:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cd34ef56gh78"
down_revision: Union[str, Sequence[str], None] = "ab12cd34ef56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "apr_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("apr_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["apr_id"], ["aprs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_apr_shares_apr_id", "apr_shares", ["apr_id"], unique=False)
    op.create_index("ix_apr_shares_id", "apr_shares", ["id"], unique=False)
    op.create_index("ix_apr_shares_token", "apr_shares", ["token"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_apr_shares_token", table_name="apr_shares")
    op.drop_index("ix_apr_shares_id", table_name="apr_shares")
    op.drop_index("ix_apr_shares_apr_id", table_name="apr_shares")
    op.drop_table("apr_shares")
