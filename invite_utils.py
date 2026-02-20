from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from urllib.parse import quote


INVITE_STATUS_PENDING = "pending"
INVITE_STATUS_ACCEPTED = "accepted"
INVITE_STATUS_EXPIRED = "expired"
INVITE_STATUS_REVOKED = "revoked"


def _invite_secret() -> str:
    return (
        os.getenv("INVITE_TOKEN_SECRET")
        or os.getenv("JWT_SECRET")
        or "dev-invite-secret"
    )


def hash_invite_token(raw_token: str) -> str:
    secret = _invite_secret().encode("utf-8")
    digest = hmac.new(secret, raw_token.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def default_invite_expiration() -> datetime:
    hours = int(os.getenv("INVITE_EXPIRY_HOURS", "168"))
    return datetime.utcnow() + timedelta(hours=hours)


def build_invite_link(raw_token: str) -> str:
    app_base_url = os.getenv("APP_BASE_URL", "http://localhost:50000").rstrip("/")
    return f"{app_base_url}/invite?token={quote(raw_token)}"


def mask_email(email: str) -> str:
    value = (email or "").strip()
    if "@" not in value:
        return value
    local, domain = value.split("@", 1)
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "*" * max(1, len(local) - 2)
    return f"{masked_local}@{domain}"
