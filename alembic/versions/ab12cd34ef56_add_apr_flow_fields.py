"""add apr flow fields and events

Revision ID: ab12cd34ef56
Revises: 8b2c2b4e7d9a
Create Date: 2026-01-23 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ab12cd34ef56"
down_revision: Union[str, Sequence[str], None] = "8b2c2b4e7d9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("aprs") as batch_op:
        batch_op.add_column(sa.Column("worksite", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("sector", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("responsible", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("activity_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("activity_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("date", sa.Date(), nullable=True))
        batch_op.create_index("ix_aprs_activity_id", ["activity_id"], unique=False)

    op.create_table(
        "apr_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("apr_id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["apr_id"], ["aprs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_apr_events_apr_id", "apr_events", ["apr_id"], unique=False)
    op.create_index("ix_apr_events_id", "apr_events", ["id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_apr_events_id", table_name="apr_events")
    op.drop_index("ix_apr_events_apr_id", table_name="apr_events")
    op.drop_table("apr_events")

    with op.batch_alter_table("aprs") as batch_op:
        batch_op.drop_index("ix_aprs_activity_id")
        batch_op.drop_column("date")
        batch_op.drop_column("activity_name")
        batch_op.drop_column("activity_id")
        batch_op.drop_column("responsible")
        batch_op.drop_column("sector")
        batch_op.drop_column("worksite")
