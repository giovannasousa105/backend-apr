"""add auth sessions and tenant rls policies

Revision ID: a9b8c7d6e5f4
Revises: f9e1a2b3c4d5
Create Date: 2026-03-06 10:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, Sequence[str], None] = "f9e1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TENANT_TABLES: tuple[str, ...] = (
    "apr_events",
    "apr_shares",
    "apr_tasks",
    "aprs",
    "invites",
    "norm_profile_events",
    "norm_profiles",
    "passos",
    "risk_items",
)


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in set(inspector.get_table_names(schema="public"))


def _ensure_auth_sessions_table(bind) -> None:
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "auth_sessions" in tables:
        return

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoke_reason", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"], unique=False)
    op.create_index("ix_auth_sessions_company_id", "auth_sessions", ["company_id"], unique=False)
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index("ix_auth_sessions_issued_at", "auth_sessions", ["issued_at"], unique=False)
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"], unique=False)
    op.create_index("ix_auth_sessions_refresh_expires_at", "auth_sessions", ["refresh_expires_at"], unique=False)
    op.create_index("ix_auth_sessions_revoked_at", "auth_sessions", ["revoked_at"], unique=False)


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
    _ensure_auth_sessions_table(bind)

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
    if "auth_sessions" not in tables:
        return
    op.drop_index("ix_auth_sessions_revoked_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_refresh_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_issued_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_token_hash", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_company_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
