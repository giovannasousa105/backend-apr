"""add cnpj, normalize roles, and company scopes

Revision ID: f7a8b9c0d1e2
Revises: c1d2e3f4g5h6
Create Date: 2026-02-20 22:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4g5h6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns(table)}
    if column.name in columns:
        return
    with op.batch_alter_table(table) as batch_op:
        batch_op.add_column(column)


def _create_index_if_missing(table: str, name: str, columns: list[str], unique: bool = False) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes(table)}
    if name in existing:
        return
    op.create_index(name, table, columns, unique=unique)


def _create_fk_if_missing(
    table: str,
    fk_name: str,
    referred_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    ondelete: str | None = None,
) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    foreign_keys = inspector.get_foreign_keys(table)
    existing_names = {fk.get("name") for fk in foreign_keys if fk.get("name")}
    if fk_name in existing_names:
        return
    for fk in foreign_keys:
        if (
            fk.get("referred_table") == referred_table
            and fk.get("constrained_columns") == local_cols
            and fk.get("referred_columns") == remote_cols
        ):
            return
    with op.batch_alter_table(table) as batch_op:
        batch_op.create_foreign_key(
            fk_name,
            referred_table,
            local_cols,
            remote_cols,
            ondelete=ondelete,
        )


def _add_company_scope_column(table: str, index_name: str, fk_name: str) -> None:
    _add_column_if_missing(
        table,
        sa.Column("company_id", sa.Integer(), nullable=True),
    )
    _create_fk_if_missing(
        table,
        fk_name,
        "companies",
        ["company_id"],
        ["id"],
        ondelete="CASCADE",
    )
    _create_index_if_missing(table, index_name, ["company_id"])


def upgrade() -> None:
    bind = op.get_bind()

    _add_column_if_missing("companies", sa.Column("cnpj", sa.String(length=32), nullable=True))
    _create_index_if_missing("companies", "ix_companies_cnpj", ["cnpj"], unique=True)

    _add_company_scope_column("passos", "ix_passos_company_id", "fk_passos_company_id")
    _add_company_scope_column("risk_items", "ix_risk_items_company_id", "fk_risk_items_company_id")
    _add_company_scope_column("apr_events", "ix_apr_events_company_id", "fk_apr_events_company_id")
    _add_company_scope_column("apr_shares", "ix_apr_shares_company_id", "fk_apr_shares_company_id")

    bind.execute(sa.text("UPDATE users SET role = 'tecnico' WHERE lower(role) IN ('user', 'técnico')"))

    bind.execute(
        sa.text(
            """
            UPDATE aprs
            SET company_id = (
                SELECT users.company_id
                FROM users
                WHERE users.id = aprs.user_id
            )
            WHERE aprs.company_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE passos
            SET company_id = (
                SELECT aprs.company_id
                FROM aprs
                WHERE aprs.id = passos.apr_id
            )
            WHERE passos.company_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE risk_items
            SET company_id = (
                SELECT aprs.company_id
                FROM aprs
                WHERE aprs.id = risk_items.apr_id
            )
            WHERE risk_items.company_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE apr_events
            SET company_id = (
                SELECT aprs.company_id
                FROM aprs
                WHERE aprs.id = apr_events.apr_id
            )
            WHERE apr_events.company_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE apr_shares
            SET company_id = (
                SELECT aprs.company_id
                FROM aprs
                WHERE aprs.id = apr_shares.apr_id
            )
            WHERE apr_shares.company_id IS NULL
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("apr_shares") as batch_op:
        batch_op.drop_constraint("fk_apr_shares_company_id", type_="foreignkey")
    with op.batch_alter_table("apr_shares") as batch_op:
        batch_op.drop_column("company_id")
    with op.batch_alter_table("apr_events") as batch_op:
        batch_op.drop_constraint("fk_apr_events_company_id", type_="foreignkey")
    with op.batch_alter_table("apr_events") as batch_op:
        batch_op.drop_column("company_id")
    with op.batch_alter_table("risk_items") as batch_op:
        batch_op.drop_constraint("fk_risk_items_company_id", type_="foreignkey")
    with op.batch_alter_table("risk_items") as batch_op:
        batch_op.drop_column("company_id")
    with op.batch_alter_table("passos") as batch_op:
        batch_op.drop_constraint("fk_passos_company_id", type_="foreignkey")
    with op.batch_alter_table("passos") as batch_op:
        batch_op.drop_column("company_id")
    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("cnpj")
