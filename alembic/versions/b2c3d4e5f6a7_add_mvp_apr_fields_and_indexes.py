"""add mvp apr fields and indexes

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-20 23:40:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "aprs" not in tables:
        return

    columns = _column_names(inspector, "aprs")
    if "external_id" not in columns:
        op.add_column("aprs", sa.Column("external_id", sa.String(length=36), nullable=True))
    if "hazards" not in columns:
        op.add_column("aprs", sa.Column("hazards", sa.Text(), nullable=False, server_default="[]"))
    if "controls" not in columns:
        op.add_column("aprs", sa.Column("controls", sa.Text(), nullable=False, server_default="[]"))

    rows = bind.execute(sa.text("SELECT id FROM aprs WHERE external_id IS NULL OR external_id = ''")).fetchall()
    for row in rows:
        bind.execute(
            sa.text("UPDATE aprs SET external_id = :external_id WHERE id = :id"),
            {"external_id": str(uuid4()), "id": row.id},
        )

    indexes = _index_names(inspector, "aprs")
    if "ix_aprs_external_id" not in indexes:
        op.create_index("ix_aprs_external_id", "aprs", ["external_id"], unique=True)
    if "ix_aprs_status" not in indexes:
        op.create_index("ix_aprs_status", "aprs", ["status"], unique=False)

    if bind.dialect.name != "sqlite":
        op.alter_column("aprs", "external_id", existing_type=sa.String(length=36), nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "aprs" not in tables:
        return

    indexes = _index_names(inspector, "aprs")
    if "ix_aprs_status" in indexes:
        op.drop_index("ix_aprs_status", table_name="aprs")
    if "ix_aprs_external_id" in indexes:
        op.drop_index("ix_aprs_external_id", table_name="aprs")

    columns = _column_names(inspector, "aprs")
    if "controls" in columns:
        op.drop_column("aprs", "controls")
    if "hazards" in columns:
        op.drop_column("aprs", "hazards")
    if "external_id" in columns:
        op.drop_column("aprs", "external_id")
