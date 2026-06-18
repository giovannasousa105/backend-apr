"""close rls for users and auth_sessions phase 1

Revision ID: f1e2d3c4b5a6
Revises: e1a2b3c4d5f7
Create Date: 2026-03-16 14:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1e2d3c4b5a6"
down_revision: Union[str, Sequence[str], None] = "e1a2b3c4d5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TENANT_TABLES: tuple[str, ...] = (
    "auth_sessions",
    "users",
)


def _execute(sql: str) -> None:
    op.execute(sa.text(sql))


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in set(inspector.get_table_names(schema="public"))


def _current_company_sql() -> str:
    return "NULLIF(current_setting('app.current_company_id', true), '')::integer"


def _current_user_sql() -> str:
    return "NULLIF(current_setting('app.current_user_id', true), '')::integer"


def _bootstrap_enabled_sql() -> str:
    return "public.app_auth_bootstrap_enabled()"


def _recreate_bootstrap_resolvers(*, enable_bootstrap: bool) -> None:
    bootstrap_set = "\n        SET app.auth_bootstrap = 'on'" if enable_bootstrap else ""

    _execute(
        f"""
        CREATE OR REPLACE FUNCTION public.auth_resolve_user_for_login(p_email text)
        RETURNS TABLE(
            id integer,
            company_id integer,
            role text,
            email text,
            password_hash text,
            is_active boolean,
            api_token text,
            mfa_enabled boolean,
            mfa_secret text,
            mfa_backup_codes text
        )
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public, pg_temp{bootstrap_set}
        AS $$
            SELECT
                u.id,
                u.company_id,
                u.role,
                u.email,
                u.password_hash,
                u.is_active,
                u.api_token,
                u.mfa_enabled,
                u.mfa_secret,
                u.mfa_backup_codes
            FROM public.users AS u
            WHERE lower(u.email) = lower(btrim(p_email))
            LIMIT 1
        $$
        """
    )
    _execute(
        f"""
        CREATE OR REPLACE FUNCTION public.auth_resolve_user_for_token(p_api_token text)
        RETURNS TABLE(
            id integer,
            company_id integer,
            role text,
            email text,
            password_hash text,
            is_active boolean,
            api_token text,
            mfa_enabled boolean,
            mfa_secret text,
            mfa_backup_codes text
        )
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public, pg_temp{bootstrap_set}
        AS $$
            SELECT
                u.id,
                u.company_id,
                u.role,
                u.email,
                u.password_hash,
                u.is_active,
                u.api_token,
                u.mfa_enabled,
                u.mfa_secret,
                u.mfa_backup_codes
            FROM public.users AS u
            WHERE u.api_token = p_api_token
            LIMIT 1
        $$
        """
    )
    _execute(
        f"""
        CREATE OR REPLACE FUNCTION public.auth_resolve_session_by_hash(p_token_hash text)
        RETURNS TABLE(
            id integer,
            user_id integer,
            company_id integer,
            token_hash text,
            expires_at timestamp without time zone,
            refresh_expires_at timestamp without time zone,
            last_seen_at timestamp without time zone,
            revoked_at timestamp without time zone,
            revoke_reason text
        )
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = public, pg_temp{bootstrap_set}
        AS $$
            SELECT
                s.id,
                s.user_id,
                s.company_id,
                s.token_hash,
                s.expires_at,
                s.refresh_expires_at,
                s.last_seen_at,
                s.revoked_at,
                s.revoke_reason
            FROM public.auth_sessions AS s
            WHERE s.token_hash = p_token_hash
            LIMIT 1
        $$
        """
    )


def _create_policy(table_name: str) -> None:
    policy_name = f'tenant_isolation_{table_name}'
    if table_name == 'users':
        predicate = (
            f"{_bootstrap_enabled_sql()} OR "
            f"company_id = {_current_company_sql()}"
        )
    elif table_name == 'auth_sessions':
        predicate = (
            f"{_bootstrap_enabled_sql()} OR "
            f"(company_id = {_current_company_sql()} AND user_id = {_current_user_sql()})"
        )
    else:
        raise ValueError(f'tabela inesperada para policy RLS: {table_name}')

    _execute(f'DROP POLICY IF EXISTS "{policy_name}" ON public."{table_name}"')
    _execute(
        f"""
        CREATE POLICY "{policy_name}" ON public."{table_name}"
        USING ({predicate})
        WITH CHECK ({predicate})
        """
    )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return

    _execute(
        """
        CREATE OR REPLACE FUNCTION public.app_auth_bootstrap_enabled()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        AS $$
            SELECT coalesce(NULLIF(current_setting('app.auth_bootstrap', true), ''), 'off') = 'on'
        $$
        """
    )
    _recreate_bootstrap_resolvers(enable_bootstrap=True)

    for table_name in _TENANT_TABLES:
        if not _table_exists(bind, table_name):
            continue
        _execute(f'ALTER TABLE public."{table_name}" ENABLE ROW LEVEL SECURITY')
        _execute(f'ALTER TABLE public."{table_name}" FORCE ROW LEVEL SECURITY')
        _create_policy(table_name)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return

    for table_name in _TENANT_TABLES:
        if not _table_exists(bind, table_name):
            continue
        _execute(f'DROP POLICY IF EXISTS "tenant_isolation_{table_name}" ON public."{table_name}"')
        _execute(f'ALTER TABLE public."{table_name}" NO FORCE ROW LEVEL SECURITY')
        _execute(f'ALTER TABLE public."{table_name}" DISABLE ROW LEVEL SECURITY')

    _recreate_bootstrap_resolvers(enable_bootstrap=False)
    _execute('DROP FUNCTION IF EXISTS public.app_auth_bootstrap_enabled()')