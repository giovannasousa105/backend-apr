"""add company plan metadata

Revision ID: c1d2e3f4g5h6
Revises: aa1b2c3d4e5f
Create Date: 2026-01-28 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4g5h6"
down_revision: Union[str, Sequence[str], None] = "aa1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("companies")}

    with op.batch_alter_table("companies") as batch_op:
        if "plan_name" not in columns:
            batch_op.add_column(
                sa.Column(
                    "plan_name",
                    sa.String(length=20),
                    nullable=False,
                    server_default=sa.text("'free'"),
                )
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("companies")}

    with op.batch_alter_table("companies") as batch_op:
        if "plan_name" in columns:
            batch_op.drop_column("plan_name")
