"""add security audit events

Revision ID: c7d8e9f0a1b2
Revises: b1c2d3e4f5a6
Create Date: 2026-03-07 00:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TENANT_TABLES: tuple[str, ...] = ("security_audit_events",)


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in set(inspector.get_table_names(schema="public"))


def _create_tenant_policy(table_name: str) -> None:
    bind = op.get_bind()
    policy_name = f"tenant_isolation_{table_name}"
    exists = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_policies
            WHERE schemaname = 'public'
              AND tablename = :table_name
              AND policyname = :policy_name
            """
        ),
        {"table_name": table_name, "policy_name": policy_name},
    ).first()
    if exists:
        return
    op.execute(
        sa.text(
            f"""
            CREATE POLICY "{policy_name}" ON public."{table_name}"
            USING (
                company_id = NULLIF(current_setting('app.current_company_id', true), '')::integer
            )
            WITH CHECK (
                company_id = NULLIF(current_setting('app.current_company_id', true), '')::integer
            )
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "security_audit_events" not in tables:
        op.create_table(
            "security_audit_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("session_id", sa.Integer(), nullable=True),
            sa.Column("event", sa.String(length=80), nullable=False),
            sa.Column("payload", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["session_id"], ["auth_sessions.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_security_audit_events_company_id", "security_audit_events", ["company_id"], unique=False)
        op.create_index("ix_security_audit_events_user_id", "security_audit_events", ["user_id"], unique=False)
        op.create_index("ix_security_audit_events_session_id", "security_audit_events", ["session_id"], unique=False)
        op.create_index("ix_security_audit_events_event", "security_audit_events", ["event"], unique=False)
        op.create_index("ix_security_audit_events_created_at", "security_audit_events", ["created_at"], unique=False)

    if bind.dialect.name != "postgresql":
        return

    for table_name in _TENANT_TABLES:
        if not _table_exists(bind, table_name):
            continue
        op.execute(sa.text(f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY'))
        op.execute(sa.text(f'ALTER TABLE public."{table_name}" FORCE ROW LEVEL SECURITY'))
        _create_tenant_policy(table_name)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table_name in _TENANT_TABLES:
            if not _table_exists(bind, table_name):
                continue
            policy_name = f"tenant_isolation_{table_name}"
            op.execute(sa.text(f'DROP POLICY IF EXISTS "{policy_name}" ON public."{table_name}"'))
            op.execute(sa.text(f'ALTER TABLE public."{table_name}" NO FORCE ROW LEVEL SECURITY'))

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "security_audit_events" not in tables:
        return

    op.drop_index("ix_security_audit_events_created_at", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_event", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_session_id", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_user_id", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_company_id", table_name="security_audit_events")
    op.drop_table("security_audit_events")
