-- =============================================================
-- MANUAL MIGRATION SCRIPT
-- Equivalent to: alembic upgrade b1c2d3e4f5a6 -> f1e2d3c4b5a6
-- Paste into Supabase SQL Editor and run.
-- =============================================================

-- ----------------------------
-- c7d8e9f0a1b2: security_audit_events
-- ----------------------------

CREATE TABLE IF NOT EXISTS public.security_audit_events (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
    session_id INTEGER REFERENCES public.auth_sessions(id) ON DELETE SET NULL,
    event VARCHAR(80) NOT NULL,
    payload TEXT,
    ip_address VARCHAR(64),
    user_agent VARCHAR(255),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_security_audit_events_company_id  ON public.security_audit_events (company_id);
CREATE INDEX IF NOT EXISTS ix_security_audit_events_user_id     ON public.security_audit_events (user_id);
CREATE INDEX IF NOT EXISTS ix_security_audit_events_session_id  ON public.security_audit_events (session_id);
CREATE INDEX IF NOT EXISTS ix_security_audit_events_event       ON public.security_audit_events (event);
CREATE INDEX IF NOT EXISTS ix_security_audit_events_created_at  ON public.security_audit_events (created_at);

ALTER TABLE public.security_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.security_audit_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenant_isolation_security_audit_events" ON public.security_audit_events;
CREATE POLICY "tenant_isolation_security_audit_events" ON public.security_audit_events
USING (
    company_id = NULLIF(current_setting('app.current_company_id', true), '')::integer
)
WITH CHECK (
    company_id = NULLIF(current_setting('app.current_company_id', true), '')::integer
);

-- ----------------------------
-- d8f9a0b1c2d3: hash chain + append-only trigger
-- ----------------------------

ALTER TABLE public.security_audit_events
    ADD COLUMN IF NOT EXISTS previous_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS event_hash    VARCHAR(64);

-- Backfill empty hash for any pre-existing rows (none expected on fresh table)
-- event_hash is required non-null; if table is already empty this is a no-op.
-- If you have existing rows without event_hash, set a placeholder first:
-- UPDATE public.security_audit_events SET event_hash = md5(random()::text) WHERE event_hash IS NULL;

ALTER TABLE public.security_audit_events ALTER COLUMN event_hash SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ix_security_audit_events_event_hash
    ON public.security_audit_events (event_hash);

CREATE OR REPLACE FUNCTION public.prevent_security_audit_events_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'security_audit_events is append-only';
END;
$$;

DROP TRIGGER IF EXISTS trg_security_audit_events_no_mutation ON public.security_audit_events;
CREATE TRIGGER trg_security_audit_events_no_mutation
BEFORE UPDATE OR DELETE ON public.security_audit_events
FOR EACH ROW EXECUTE FUNCTION public.prevent_security_audit_events_mutation();

-- ----------------------------
-- e1a2b3c4d5f7 + f1e2d3c4b5a6: auth functions + RLS
-- (f1e2d3c4b5a6 supersedes e1a2b3c4d5f7 — bootstrap support included)
-- ----------------------------

CREATE OR REPLACE FUNCTION public.app_current_company_id()
RETURNS integer LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.current_company_id', true), '')::integer
$$;

CREATE OR REPLACE FUNCTION public.app_current_user_id()
RETURNS integer LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.current_user_id', true), '')::integer
$$;

CREATE OR REPLACE FUNCTION public.app_current_user_role()
RETURNS text LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.current_user_role', true), '')::text
$$;

CREATE OR REPLACE FUNCTION public.app_auth_bootstrap_enabled()
RETURNS boolean LANGUAGE sql STABLE AS $$
    SELECT coalesce(NULLIF(current_setting('app.auth_bootstrap', true), ''), 'off') = 'on'
$$;

CREATE OR REPLACE FUNCTION public.auth_resolve_user_for_login(p_email text)
RETURNS TABLE(
    id integer, company_id integer, role text, email text,
    password_hash text, is_active boolean, api_token text,
    mfa_enabled boolean, mfa_secret text, mfa_backup_codes text
)
LANGUAGE sql SECURITY DEFINER
SET search_path = public, pg_temp
SET app.auth_bootstrap = 'on'
AS $$
    SELECT u.id, u.company_id, u.role, u.email, u.password_hash,
           u.is_active, u.api_token, u.mfa_enabled, u.mfa_secret, u.mfa_backup_codes
    FROM public.users AS u
    WHERE lower(u.email) = lower(btrim(p_email))
    LIMIT 1
$$;

CREATE OR REPLACE FUNCTION public.auth_resolve_user_for_token(p_api_token text)
RETURNS TABLE(
    id integer, company_id integer, role text, email text,
    password_hash text, is_active boolean, api_token text,
    mfa_enabled boolean, mfa_secret text, mfa_backup_codes text
)
LANGUAGE sql SECURITY DEFINER
SET search_path = public, pg_temp
SET app.auth_bootstrap = 'on'
AS $$
    SELECT u.id, u.company_id, u.role, u.email, u.password_hash,
           u.is_active, u.api_token, u.mfa_enabled, u.mfa_secret, u.mfa_backup_codes
    FROM public.users AS u
    WHERE u.api_token = p_api_token
    LIMIT 1
$$;

CREATE OR REPLACE FUNCTION public.auth_resolve_session_by_hash(p_token_hash text)
RETURNS TABLE(
    id integer, user_id integer, company_id integer, token_hash text,
    expires_at timestamp without time zone, refresh_expires_at timestamp without time zone,
    last_seen_at timestamp without time zone, revoked_at timestamp without time zone,
    revoke_reason text
)
LANGUAGE sql SECURITY DEFINER
SET search_path = public, pg_temp
SET app.auth_bootstrap = 'on'
AS $$
    SELECT s.id, s.user_id, s.company_id, s.token_hash,
           s.expires_at, s.refresh_expires_at, s.last_seen_at,
           s.revoked_at, s.revoke_reason
    FROM public.auth_sessions AS s
    WHERE s.token_hash = p_token_hash
    LIMIT 1
$$;

-- Enable RLS + FORCE on users and auth_sessions
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenant_isolation_users" ON public.users;
CREATE POLICY "tenant_isolation_users" ON public.users
USING (
    public.app_auth_bootstrap_enabled()
    OR company_id = NULLIF(current_setting('app.current_company_id', true), '')::integer
)
WITH CHECK (
    public.app_auth_bootstrap_enabled()
    OR company_id = NULLIF(current_setting('app.current_company_id', true), '')::integer
);

ALTER TABLE public.auth_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_sessions FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenant_isolation_auth_sessions" ON public.auth_sessions;
CREATE POLICY "tenant_isolation_auth_sessions" ON public.auth_sessions
USING (
    public.app_auth_bootstrap_enabled()
    OR (
        company_id = NULLIF(current_setting('app.current_company_id', true), '')::integer
        AND user_id  = NULLIF(current_setting('app.current_user_id',  true), '')::integer
    )
)
WITH CHECK (
    public.app_auth_bootstrap_enabled()
    OR (
        company_id = NULLIF(current_setting('app.current_company_id', true), '')::integer
        AND user_id  = NULLIF(current_setting('app.current_user_id',  true), '')::integer
    )
);

-- ----------------------------
-- Tell Alembic the DB is now at head
-- ----------------------------
UPDATE public.alembic_version SET version_num = 'f1e2d3c4b5a6';
