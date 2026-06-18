from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from auth_utils import session_token_hash
from models import AuthSession, SecurityAuditEvent, User
from security_context import resolve_session_by_hash, set_security_context


def _safe_trim(value: str | None, max_len: int) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    return text[:max_len]


def resolve_auth_session(db: Session, token: str | None) -> AuthSession | None:
    if not token or "." not in token:
        return None
    session_identity = resolve_session_by_hash(db, session_token_hash(token))
    if not session_identity:
        return None
    set_security_context(db, company_id=session_identity.company_id, user_id=session_identity.user_id)
    return db.get(AuthSession, session_identity.id)


def _canonical_payload(value: dict[str, Any] | None) -> str:
    data = value if isinstance(value, dict) else {}
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_chain_entry(
    *,
    company_id: int | None,
    user_id: int | None,
    session_id: int | None,
    event: str,
    payload_canonical: str,
    ip_address: str | None,
    user_agent: str | None,
    created_at: datetime,
    previous_hash: str | None,
) -> str:
    created_at_utc = created_at.replace(tzinfo=None).isoformat(timespec="microseconds")
    material = "\n".join(
        [
            str(company_id or ""),
            str(user_id or ""),
            str(session_id or ""),
            event,
            payload_canonical,
            ip_address or "",
            user_agent or "",
            created_at_utc,
            previous_hash or "",
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _lock_company_chain(db: Session, company_id: int | None) -> None:
    if not company_id:
        return
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(company_id)})


def _last_event_hash_for_company(db: Session, company_id: int | None) -> str | None:
    if not company_id:
        return None
    return db.execute(
        select(SecurityAuditEvent.event_hash)
        .where(SecurityAuditEvent.company_id == company_id)
        .order_by(SecurityAuditEvent.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def parse_security_event_payload(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        decoded = json.loads(value)
    except Exception:
        return {"_raw": str(value)}
    return decoded if isinstance(decoded, dict) else {"_raw": decoded}


def record_security_event(
    db: Session,
    *,
    user: User,
    event: str,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    session: AuthSession | None = None,
) -> SecurityAuditEvent:
    _lock_company_chain(db, user.company_id)
    previous_hash = _last_event_hash_for_company(db, user.company_id)
    event_name = _safe_trim(event, 80) or "unknown"
    ip_address_safe = _safe_trim(ip_address, 64)
    user_agent_safe = _safe_trim(user_agent, 255)
    created_at = datetime.utcnow()
    payload_canonical = _canonical_payload(payload)

    item = SecurityAuditEvent(
        company_id=user.company_id,
        user_id=user.id,
        session_id=session.id if session else None,
        event=event_name,
        payload=payload_canonical,
        ip_address=ip_address_safe,
        user_agent=user_agent_safe,
        previous_hash=previous_hash,
        event_hash=_hash_chain_entry(
            company_id=user.company_id,
            user_id=user.id,
            session_id=session.id if session else None,
            event=event_name,
            payload_canonical=payload_canonical,
            ip_address=ip_address_safe,
            user_agent=user_agent_safe,
            created_at=created_at,
            previous_hash=previous_hash,
        ),
        created_at=created_at,
    )
    db.add(item)
    db.flush()
    return item