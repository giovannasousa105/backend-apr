"""fix legacy catalog column names

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_columns(inspector, table_name: str) -> set[str]:
    if not inspector.has_table(table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _rename_column_if_needed(
    *,
    table_name: str,
    target: str,
    aliases: list[str],
    inspector,
) -> None:
    columns = _table_columns(inspector, table_name)
    if not columns or target in columns:
        return

    for alias in aliases:
        if alias in columns:
            op.execute(
                sa.text(
                    f'ALTER TABLE "{table_name}" RENAME COLUMN "{alias}" TO "{target}"'
                )
            )
            break


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _rename_column_if_needed(
        table_name="epis",
        target="epi",
        aliases=["name", "epi_name"],
        inspector=inspector,
    )
    inspector = sa.inspect(bind)
    _rename_column_if_needed(
        table_name="epis",
        target="descricao",
        aliases=["description"],
        inspector=inspector,
    )
    inspector = sa.inspect(bind)
    _rename_column_if_needed(
        table_name="epis",
        target="normas",
        aliases=["standards"],
        inspector=inspector,
    )

    inspector = sa.inspect(bind)
    _rename_column_if_needed(
        table_name="perigos",
        target="perigo",
        aliases=["name", "hazard"],
        inspector=inspector,
    )
    inspector = sa.inspect(bind)
    _rename_column_if_needed(
        table_name="perigos",
        target="consequencias",
        aliases=["consequences", "risks"],
        inspector=inspector,
    )
    inspector = sa.inspect(bind)
    _rename_column_if_needed(
        table_name="perigos",
        target="salvaguardas",
        aliases=["safeguards", "controls"],
        inspector=inspector,
    )


def downgrade() -> None:
    # No-op: this migration only normalizes legacy column names.
    pass
