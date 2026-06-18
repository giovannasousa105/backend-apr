"""Security context helpers for tenant/user scoped database access."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import AuthSession, User


@dataclass(frozen=True)
class AuthBootstrapUser:
    id: int
    company_id: int | None
    role: str | None
    email: str
    password_hash: str
    is_active: bool
    api_token: str
    mfa_enabled: bool
    mfa_secret: str | None
    mfa_backup_codes_json: str | None


@dataclass(frozen=True)
class AuthBootstrapSession:
    id: int
    user_id: int
    company_id: int | None
    token_hash: str
    expires_at: datetime
    refresh_expires_at: datetime
    last_seen_at: datetime | None
    revoked_at: datetime | None
    revoke_reason: str | None


def _is_postgresql(db: Session) -> bool:
    return db.get_bind().dialect.name == "postgresql"


def set_security_context(
    db: Session,
    *,
    company_id: int | None,
    user_id: int | None = None,
    user_role: str | None = None,
    auth_bootstrap: bool = False,
) -> None:
    if not _is_postgresql(db):
        return
    db.execute(
        text(
            """
            SELECT
                set_config('app.current_company_id', :company_id, false),
                set_config('app.current_user_id', :user_id, false),
                set_config('app.current_user_role', :user_role, false),
                set_config('app.auth_bootstrap', :auth_bootstrap, false)
            """
        ),
        {
            "company_id": str(company_id or 0),
            "user_id": str(user_id or 0),
            "user_role": (user_role or "")[:64],
            "auth_bootstrap": "on" if auth_bootstrap else "off",
        },
    )


def _resolve_user_from_row(row) -> AuthBootstrapUser | None:
    if not row:
        return None
    return AuthBootstrapUser(
        id=int(row["id"]),
        company_id=int(row["company_id"]) if row["company_id"] is not None else None,
        role=str(row["role"]) if row["role"] is not None else None,
        email=str(row["email"]),
        password_hash=str(row["password_hash"] or ""),
        is_active=bool(row["is_active"]),
        api_token=str(row["api_token"] or ""),
        mfa_enabled=bool(row["mfa_enabled"]),
        mfa_secret=str(row["mfa_secret"]) if row["mfa_secret"] is not None else None,
        mfa_backup_codes_json=(str(row["mfa_backup_codes"]) if row.get("mfa_backup_codes") is not None else None),
    )


def _resolve_session_from_row(row) -> AuthBootstrapSession | None:
    if not row:
        return None
    return AuthBootstrapSession(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        company_id=int(row["company_id"]) if row["company_id"] is not None else None,
        token_hash=str(row["token_hash"] or ""),
        expires_at=row["expires_at"],
        refresh_expires_at=row["refresh_expires_at"],
        last_seen_at=row["last_seen_at"],
        revoked_at=row["revoked_at"],
        revoke_reason=str(row["revoke_reason"]) if row["revoke_reason"] is not None else None,
    )


def resolve_user_for_login(db: Session, email: str) -> AuthBootstrapUser | None:
    normalized_email = email.strip().lower()
    if _is_postgresql(db):
        try:
            row = db.execute(text("SELECT * FROM public.auth_resolve_user_for_login(:email)"), {"email": normalized_email}).mappings().first()
            resolved = _resolve_user_from_row(row)
            if resolved is not None:
                return resolved
        except SQLAlchemyError:
            db.rollback()

    user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if not user:
        return None
    return AuthBootstrapUser(
        id=int(user.id),
        company_id=int(user.company_id) if user.company_id is not None else None,
        role=user.role,
        email=user.email,
        password_hash=user.password_hash,
        is_active=bool(user.is_active),
        api_token=user.api_token,
        mfa_enabled=bool(user.mfa_enabled),
        mfa_secret=user.mfa_secret,
        mfa_backup_codes_json=user.mfa_backup_codes_json,
    )


def resolve_user_for_token(db: Session, api_token: str) -> AuthBootstrapUser | None:
    if _is_postgresql(db):
        try:
            row = db.execute(text("SELECT * FROM public.auth_resolve_user_for_token(:api_token)"), {"api_token": api_token}).mappings().first()
            resolved = _resolve_user_from_row(row)
            if resolved is not None:
                return resolved
        except SQLAlchemyError:
            db.rollback()

    user = db.execute(select(User).where(User.api_token == api_token)).scalar_one_or_none()
    if not user:
        return None
    return AuthBootstrapUser(
        id=int(user.id),
        company_id=int(user.company_id) if user.company_id is not None else None,
        role=user.role,
        email=user.email,
        password_hash=user.password_hash,
        is_active=bool(user.is_active),
        api_token=user.api_token,
        mfa_enabled=bool(user.mfa_enabled),
        mfa_secret=user.mfa_secret,
        mfa_backup_codes_json=user.mfa_backup_codes_json,
    )


def resolve_session_by_hash(db: Session, token_hash: str) -> AuthBootstrapSession | None:
    if _is_postgresql(db):
        try:
            row = db.execute(text("SELECT * FROM public.auth_resolve_session_by_hash(:token_hash)"), {"token_hash": token_hash}).mappings().first()
            resolved = _resolve_session_from_row(row)
            if resolved is not None:
                return resolved
        except SQLAlchemyError:
            db.rollback()

    session = db.execute(select(AuthSession).where(AuthSession.token_hash == token_hash)).scalar_one_or_none()
    if not session:
        return None
    return AuthBootstrapSession(
        id=int(session.id),
        user_id=int(session.user_id),
        company_id=int(session.company_id) if session.company_id is not None else None,
        token_hash=session.token_hash,
        expires_at=session.expires_at,
        refresh_expires_at=session.refresh_expires_at,
        last_seen_at=session.last_seen_at,
        revoked_at=session.revoked_at,
        revoke_reason=session.revoke_reason,
    )
