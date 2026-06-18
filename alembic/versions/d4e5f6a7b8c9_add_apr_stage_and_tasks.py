"""add apr current stage and tasks

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-25 20:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
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

    if "current_stage" not in apr_columns:
        with op.batch_alter_table("aprs") as batch_op:
            batch_op.add_column(
                sa.Column("current_stage", sa.String(length=20), nullable=False, server_default="criar")
            )
    bind.execute(sa.text("UPDATE aprs SET current_stage = 'criar' WHERE current_stage IS NULL OR current_stage = ''"))
    _create_index_if_missing("aprs", "ix_aprs_current_stage", ["current_stage"])

    if "apr_tasks" not in inspector.get_table_names():
        op.create_table(
            "apr_tasks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("apr_id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=True),
            sa.Column("step_id", sa.Integer(), nullable=True),
            sa.Column("type", sa.String(length=40), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("assigned_to_user_id", sa.Integer(), nullable=True),
            sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
            sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
            sa.Column("due_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["apr_id"], ["aprs.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["step_id"], ["passos.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_apr_tasks_id", "apr_tasks", ["id"], unique=False)

    _create_index_if_missing("apr_tasks", "ix_apr_tasks_apr_id", ["apr_id"])
    _create_index_if_missing("apr_tasks", "ix_apr_tasks_company_id", ["company_id"])
    _create_index_if_missing("apr_tasks", "ix_apr_tasks_step_id", ["step_id"])
    _create_index_if_missing("apr_tasks", "ix_apr_tasks_assigned_to_user_id", ["assigned_to_user_id"])
    _create_index_if_missing("apr_tasks", "ix_apr_tasks_requested_by_user_id", ["requested_by_user_id"])
    _create_index_if_missing("apr_tasks", "ix_apr_tasks_status", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "apr_tasks" in tables:
        op.drop_table("apr_tasks")

    apr_columns = {col["name"] for col in inspector.get_columns("aprs")}
    if "current_stage" in apr_columns:
        index_names = {idx["name"] for idx in inspector.get_indexes("aprs")}
        with op.batch_alter_table("aprs") as batch_op:
            if "ix_aprs_current_stage" in index_names:
                batch_op.drop_index("ix_aprs_current_stage")
            batch_op.drop_column("current_stage")
