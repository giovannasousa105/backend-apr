from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from auth_utils import _session_refresh_grace_minutes, allow_legacy_api_tokens, session_token_hash
from models import AuthSession, User
from security_context import AuthBootstrapSession, resolve_session_by_hash, set_security_context


_LAST_SEEN_INTERVAL_S = 300


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_trim(value: str | None, max_len: int) -> str | None:
    if not value:
        return None
    text_val = value.strip()
    if not text_val:
        return None
    return text_val[:max_len]


def _as_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC). Treats naive datetimes as UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _maybe_touch_session(
    db: Session,
    session_identity: AuthBootstrapSession,
    now: datetime,
) -> None:
    """Update last_seen_at only when stale, avoiding a round-trip on every request."""
    last = session_identity.last_seen_at
    if last is not None and (_as_utc(now) - _as_utc(last)).total_seconds() < _LAST_SEEN_INTERVAL_S:
        return
    db.execute(
        text("UPDATE auth_sessions SET last_seen_at = :now WHERE id = :id"),
        {"now": now.replace(tzinfo=None), "id": session_identity.id},
    )


def _load_session_under_context(
    db: Session,
    session_id: int,
    *,
    company_id: int | None,
    user_id: int,
) -> AuthSession | None:
    """Load a writable AuthSession ORM object under the correct security context.
    Used by refresh and revoke flows that need to write to the session record.
    Not used in the hot read-path (require_active_session) to avoid extra round-trips.
    """
    set_security_context(db, company_id=company_id, user_id=user_id)
    return db.get(AuthSession, session_id)


def register_session(
    db: Session,
    *,
    user: User,
    token: str,
    expires_at: datetime,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuthSession:
    refresh_expires_at = expires_at + timedelta(minutes=_session_refresh_grace_minutes())
    session = AuthSession(
        user_id=user.id,
        company_id=user.company_id,
        token_hash=session_token_hash(token),
        ip_address=_safe_trim(ip_address, 64),
        user_agent=_safe_trim(user_agent, 255),
        issued_at=_utc_now(),
        expires_at=expires_at,
        refresh_expires_at=refresh_expires_at,
        last_seen_at=_utc_now(),
    )
    db.add(session)
    db.flush()
    return session


def require_active_session(
    db: Session,
    token: str,
    *,
    allow_missing_legacy: bool | None = None,
) -> AuthBootstrapSession | None:
    """Validate that the session token is active.

    Returns the resolved AuthBootstrapSession so callers can reuse its user_id
    and company_id without an extra round-trip. Returns None only for legacy
    API-token requests where no session row exists.
    """
    allow_legacy = allow_legacy_api_tokens() if allow_missing_legacy is None else allow_missing_legacy
    if "." not in (token or ""):
        if allow_legacy:
            return None
        raise ValueError("legacy_token_disabled")

    token_hash = session_token_hash(token)
    session_identity = resolve_session_by_hash(db, token_hash)
    if not session_identity:
        if allow_legacy:
            return None
        raise ValueError("session_not_found")
    if session_identity.revoked_at is not None:
        raise ValueError("session_revoked")

    now = _utc_now()
    if _as_utc(session_identity.expires_at) < now:
        raise ValueError("session_expired")

    _maybe_touch_session(db, session_identity, now)
    return session_identity


def require_refresh_session(db: Session, token: str) -> AuthSession:
    token_hash = session_token_hash(token)
    session_identity = resolve_session_by_hash(db, token_hash)
    if not session_identity:
        raise ValueError("session_not_found")
    if session_identity.revoked_at is not None:
        raise ValueError("session_revoked")

    now = _utc_now()
    if _as_utc(session_identity.refresh_expires_at) < now:
        raise ValueError("session_refresh_expired")

    session = _load_session_under_context(
        db,
        session_identity.id,
        company_id=session_identity.company_id,
        user_id=session_identity.user_id,
    )
    if not session:
        raise ValueError("session_not_found")
    if session.revoked_at is not None:
        raise ValueError("session_revoked")
    return session


def revoke_session(db: Session, token: str, reason: str = "logout") -> bool:
    token_hash = session_token_hash(token)
    session_identity = resolve_session_by_hash(db, token_hash)
    if not session_identity:
        return False

    session = _load_session_under_context(
        db,
        session_identity.id,
        company_id=session_identity.company_id,
        user_id=session_identity.user_id,
    )
    if not session:
        return False
    if session.revoked_at is None:
        session.revoked_at = _utc_now()
        session.revoke_reason = _safe_trim(reason, 64)
        db.flush()
    return True


def revoke_all_user_sessions(db: Session, user_id: int, reason: str = "logout_all") -> int:
    sessions = db.execute(
        select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    ).scalars().all()
    if not sessions:
        return 0
    now = _utc_now()
    revoke_reason = _safe_trim(reason, 64)
    for session in sessions:
        session.revoked_at = now
        session.revoke_reason = revoke_reason
    db.flush()
    return len(sessions)
