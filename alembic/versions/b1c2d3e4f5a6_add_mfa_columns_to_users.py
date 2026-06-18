"""add mfa columns to users

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-03-06 11:25:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "a9b8c7d6e5f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    columns = _column_names("users")
    with op.batch_alter_table("users") as batch_op:
        if "mfa_enabled" not in columns:
            batch_op.add_column(sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "mfa_secret" not in columns:
            batch_op.add_column(sa.Column("mfa_secret", sa.String(length=64), nullable=True))
        if "mfa_backup_codes" not in columns:
            batch_op.add_column(sa.Column("mfa_backup_codes", sa.Text(), nullable=True))

    op.execute(sa.text("UPDATE users SET mfa_enabled = false WHERE mfa_enabled IS NULL"))


def downgrade() -> None:
    columns = _column_names("users")
    with op.batch_alter_table("users") as batch_op:
        if "mfa_backup_codes" in columns:
            batch_op.drop_column("mfa_backup_codes")
        if "mfa_secret" in columns:
            batch_op.drop_column("mfa_secret")
        if "mfa_enabled" in columns:
            batch_op.drop_column("mfa_enabled")
