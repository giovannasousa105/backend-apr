"""add auth bootstrap security context functions

Revision ID: e1a2b3c4d5f7
Revises: d8f9a0b1c2d3
Create Date: 2026-03-16 11:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1a2b3c4d5f7"
down_revision: Union[str, Sequence[str], None] = "d8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _execute(sql: str) -> None:
    op.execute(sa.text(sql))


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    _execute(
        """
        CREATE OR REPLACE FUNCTION public.app_current_company_id()
        RETURNS integer
        LANGUAGE sql
        STABLE
        AS $$
            SELECT NULLIF(current_setting('app.current_company_id', true), '')::integer
        $$
        """
    )
    _execute(
        """
        CREATE OR REPLACE FUNCTION public.app_current_user_id()
        RETURNS integer
        LANGUAGE sql
        STABLE
        AS $$
            SELECT NULLIF(current_setting('app.current_user_id', true), '')::integer
        $$
        """
    )
    _execute(
        """
        CREATE OR REPLACE FUNCTION public.app_current_user_role()
        RETURNS text
        LANGUAGE sql
        STABLE
        AS $$
            SELECT NULLIF(current_setting('app.current_user_role', true), '')::text
        $$
        """
    )
    _execute(
        """
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
        SET search_path = public, pg_temp
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
        """
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
        SET search_path = public, pg_temp
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
        """
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
        SET search_path = public, pg_temp
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


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    _execute("DROP FUNCTION IF EXISTS public.auth_resolve_session_by_hash(text)")
    _execute("DROP FUNCTION IF EXISTS public.auth_resolve_user_for_token(text)")
    _execute("DROP FUNCTION IF EXISTS public.auth_resolve_user_for_login(text)")
    _execute("DROP FUNCTION IF EXISTS public.app_current_user_role()")
    _execute("DROP FUNCTION IF EXISTS public.app_current_user_id()")
    _execute("DROP FUNCTION IF EXISTS public.app_current_company_id()")
