from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Tuple


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def hash_password(password: str, iterations: int | None = None) -> str:
    if iterations is None:
        iterations = int(os.getenv("PASSWORD_HASH_ITERATIONS", "120000"))
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64encode(salt)}${_b64encode(dk)}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        algo, iter_str, salt_b64, hash_b64 = hashed.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        salt = _b64decode(salt_b64)
        expected = _b64decode(hash_b64)
    except Exception:
        return False

    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(dk, expected)


def generate_token() -> str:
    return secrets.token_hex(32)


def _session_secret() -> bytes:
    value = os.getenv("JWT_SECRET", "change-me")
    return value.encode("utf-8")


def _session_ttl_minutes() -> int:
    return int(os.getenv("SESSION_TTL_MINUTES", "480"))


def _session_refresh_grace_minutes() -> int:
    return int(os.getenv("SESSION_REFRESH_GRACE_MINUTES", "10080"))


def _session_sign(payload: str) -> str:
    return hmac.new(_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_session_token(api_token: str, *, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    exp = int((current + timedelta(minutes=_session_ttl_minutes())).timestamp())
    payload = f"{exp}.{api_token}"
    sig = _session_sign(payload)
    return f"v1.{exp}.{api_token}.{sig}"


def resolve_api_token_from_session(
    token: str,
    *,
    allow_expired: bool = False,
    now: datetime | None = None,
) -> Tuple[str, bool]:
    value = (token or "").strip()
    # Backward compatibility: legacy random API token without expiry.
    if "." not in value:
        return value, False

    parts = value.split(".")
    if len(parts) != 4 or parts[0] != "v1":
        return value, False

    _, exp_raw, api_token, sig = parts
    try:
        exp = int(exp_raw)
    except ValueError:
        raise ValueError("invalid_session_token")

    payload = f"{exp}.{api_token}"
    expected = _session_sign(payload)
    if not hmac.compare_digest(expected, sig):
        raise ValueError("invalid_session_signature")

    current_ts = int((now or datetime.now(timezone.utc)).timestamp())
    if exp >= current_ts:
        return api_token, False

    if not allow_expired:
        raise ValueError("session_expired")

    grace_limit = exp + (_session_refresh_grace_minutes() * 60)
    if current_ts > grace_limit:
        raise ValueError("session_refresh_expired")
    return api_token, True
