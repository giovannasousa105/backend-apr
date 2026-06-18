from __future__ import annotations

from fastapi import Depends, Header, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from api_errors import ApiError
from auth_utils import resolve_api_token_from_session
from database import get_db
from models import Company, User
from rbac import ROLE_VISUALIZADOR, VALID_ROLES, is_admin, normalize_role
from security_context import AuthBootstrapSession, resolve_user_for_token, set_security_context
from session_security import require_active_session


def _extract_token(authorization: str | None, x_api_token: str | None) -> str | None:
    if authorization:
        value = authorization.strip()
        if value.lower().startswith("bearer "):
            return value.split(" ", 1)[1].strip()
    if x_api_token:
        return x_api_token.strip()
    return None


def _is_postgresql(db: Session) -> bool:
    return db.get_bind().dialect.name == "postgresql"


def _load_authenticated_user(
    db: Session,
    api_token: str,
    session_identity: AuthBootstrapSession | None,
) -> User:
    """Load authenticated user from DB.

    When session_identity is provided (normal session flow), skips resolve_user_for_token
    and combines set_security_context + User+Company load into one round-trip via CTE.
    Falls back to the three-query path for legacy API-token requests.
    """
    if session_identity is not None and _is_postgresql(db):
        user_id = session_identity.user_id
        company_id = session_identity.company_id

        row = db.execute(
            text("""
                WITH ctx AS (
                    SELECT
                        set_config('app.current_company_id', :cid, false),
                        set_config('app.current_user_id', :uid, false),
                        set_config('app.auth_bootstrap', 'off', false)
                )
                SELECT
                    u.id, u.email, u.name, u.role, u.company_id, u.is_active,
                    u.api_token, u.mfa_enabled, u.mfa_secret, u.mfa_backup_codes,
                    set_config('app.current_user_role', coalesce(u.role, ''), false) as _role_ctx,
                    c.id    AS c_id,
                    c.name  AS c_name,
                    c.plan_name AS c_plan_name
                FROM public.users u
                LEFT JOIN public.companies c ON c.id = u.company_id, ctx
                WHERE u.id = :user_id
            """),
            {"cid": str(company_id or 0), "uid": str(user_id), "user_id": user_id},
        ).mappings().first()

        if not row or not row["is_active"]:
            raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")

        company: Company | None = None
        if row["c_id"] is not None:
            company = Company(
                id=row["c_id"],
                name=row["c_name"],
                plan_name=row["c_plan_name"],
            )

        user = User(
            id=row["id"],
            email=row["email"],
            name=row["name"],
            role=row["role"],
            company_id=row["company_id"],
            is_active=row["is_active"],
            api_token=row["api_token"],
            mfa_enabled=row["mfa_enabled"],
            mfa_secret=row["mfa_secret"],
            mfa_backup_codes_json=row["mfa_backup_codes"],
        )
        user.__dict__["company"] = company

        normalized_role = normalize_role(row["role"])
        user.role = normalized_role if normalized_role in VALID_ROLES else ROLE_VISUALIZADOR
        return user

    # Legacy API-token path (no session row): keep three-query flow
    resolved = resolve_user_for_token(db, api_token)
    if not resolved or not resolved.is_active:
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")

    set_security_context(db, company_id=resolved.company_id, user_id=resolved.id, user_role=resolved.role)

    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    user = db.execute(
        select(User).where(User.id == resolved.id).options(joinedload(User.company))
    ).unique().scalar_one_or_none()
    if not user or not user.is_active:
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")

    normalized_role = normalize_role(user.role or resolved.role)
    user.role = normalized_role if normalized_role in VALID_ROLES else ROLE_VISUALIZADOR
    return user


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_token(authorization, x_api_token)
    if not token:
        raise ApiError(status_code=401, code="auth_required", message="Token nao informado", field="authorization")

    try:
        api_token, _expired = resolve_api_token_from_session(token)
    except ValueError as exc:
        message = str(exc)
        if message in {"session_expired", "session_refresh_expired"}:
            raise ApiError(status_code=401, code="token_expired", message="Sessao expirada", field="authorization")
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")

    try:
        session_identity = require_active_session(db, token)
    except ValueError as exc:
        reason = str(exc)
        if reason in {"session_expired", "session_revoked"}:
            raise ApiError(status_code=401, code="token_expired", message="Sessao expirada", field="authorization")
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")

    return _load_authenticated_user(db, api_token, session_identity)


def get_current_user_optional(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    db: Session = Depends(get_db),
) -> User | None:
    token = _extract_token(authorization, x_api_token)
    if not token:
        return None
    try:
        api_token, _expired = resolve_api_token_from_session(token)
    except ValueError as exc:
        message = str(exc)
        if message in {"session_expired", "session_refresh_expired"}:
            raise ApiError(status_code=401, code="token_expired", message="Sessao expirada", field="authorization")
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")

    try:
        session_identity = require_active_session(db, token)
    except ValueError as exc:
        reason = str(exc)
        if reason in {"session_expired", "session_revoked"}:
            raise ApiError(status_code=401, code="token_expired", message="Sessao expirada", field="authorization")
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")

    return _load_authenticated_user(db, api_token, session_identity)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not is_admin(user.role):
        raise ApiError(status_code=403, code="forbidden", message="Acesso restrito a admin", field="role")
    return user
