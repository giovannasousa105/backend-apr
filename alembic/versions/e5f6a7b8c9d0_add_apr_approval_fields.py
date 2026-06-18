"""add apr approval fields

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-25 22:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_index_if_missing(table: str, name: str, columns: list[str], unique: bool = False) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes(table)}
    if name in existing:
        return
    op.create_index(name, table, columns, unique=unique)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    apr_columns = {col["name"] for col in inspector.get_columns("aprs")}

    with op.batch_alter_table("aprs") as batch_op:
        if "approved_by_user_id" not in apr_columns:
            batch_op.add_column(sa.Column("approved_by_user_id", sa.Integer(), nullable=True))
        if "approved_by_name" not in apr_columns:
            batch_op.add_column(sa.Column("approved_by_name", sa.String(length=255), nullable=True))
        if "approved_at" not in apr_columns:
            batch_op.add_column(sa.Column("approved_at", sa.DateTime(), nullable=True))

    foreign_keys = inspector.get_foreign_keys("aprs")
    fk_names = {fk.get("name") for fk in foreign_keys if fk.get("name")}
    if "fk_aprs_approved_by_user_id" not in fk_names:
        with op.batch_alter_table("aprs") as batch_op:
            batch_op.create_foreign_key(
                "fk_aprs_approved_by_user_id",
                "users",
                ["approved_by_user_id"],
                ["id"],
                ondelete="SET NULL",
            )

    _create_index_if_missing("aprs", "ix_aprs_approved_by_user_id", ["approved_by_user_id"])

    bind.execute(
        sa.text(
            """
            UPDATE aprs
            SET approved_by_name = NULLIF(trim(approved_by_name), '')
            WHERE approved_by_name IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    apr_columns = {col["name"] for col in inspector.get_columns("aprs")}
    index_names = {idx["name"] for idx in inspector.get_indexes("aprs")}
    fk_names = {fk.get("name") for fk in inspector.get_foreign_keys("aprs") if fk.get("name")}

    with op.batch_alter_table("aprs") as batch_op:
        if "ix_aprs_approved_by_user_id" in index_names:
            batch_op.drop_index("ix_aprs_approved_by_user_id")
        if "fk_aprs_approved_by_user_id" in fk_names:
            batch_op.drop_constraint("fk_aprs_approved_by_user_id", type_="foreignkey")
        if "approved_at" in apr_columns:
            batch_op.drop_column("approved_at")
        if "approved_by_name" in apr_columns:
            batch_op.drop_column("approved_by_name")
        if "approved_by_user_id" in apr_columns:
            batch_op.drop_column("approved_by_user_id")
