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
    value = (os.getenv("JWT_SECRET") or "").strip()
    if not value or value.lower() in {"change-me", "changeme", "default", "secret"}:
        raise RuntimeError("JWT_SECRET inseguro ou nao configurado")
    if len(value) < 32:
        raise RuntimeError("JWT_SECRET deve ter no minimo 32 caracteres")
    return value.encode("utf-8")


def _session_ttl_minutes() -> int:
    return int(os.getenv("SESSION_TTL_MINUTES", "60"))


def _session_refresh_grace_minutes() -> int:
    return int(os.getenv("SESSION_REFRESH_GRACE_MINUTES", "1440"))


def _session_sign(payload: str) -> str:
    return hmac.new(_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def allow_legacy_api_tokens() -> bool:
    # Migration escape hatch: keep disabled by default for secure-by-default sessions.
    return _is_truthy(os.getenv("ALLOW_LEGACY_API_TOKENS", "false"))


def issue_session_token(api_token: str, *, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    exp = int((current + timedelta(minutes=_session_ttl_minutes())).timestamp())
    nonce = secrets.token_hex(8)
    payload = f"{exp}.{nonce}.{api_token}"
    sig = _session_sign(payload)
    return f"v2.{exp}.{nonce}.{api_token}.{sig}"


def session_expires_at(token: str) -> datetime | None:
    value = (token or "").strip()
    parts = value.split(".")
    if len(parts) == 5 and parts[0] == "v2":
        try:
            exp = int(parts[1])
        except ValueError:
            return None
        return datetime.fromtimestamp(exp, tz=timezone.utc)

    if len(parts) != 4 or parts[0] != "v1":
        return None
    try:
        exp = int(parts[1])
    except ValueError:
        return None
    return datetime.fromtimestamp(exp, tz=timezone.utc)


def session_token_hash(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def resolve_api_token_from_session(
    token: str,
    *,
    allow_expired: bool = False,
    now: datetime | None = None,
) -> Tuple[str, bool]:
    value = (token or "").strip()
    if "." not in value:
        if allow_legacy_api_tokens():
            return value, False
        raise ValueError("legacy_token_disabled")

    parts = value.split(".")
    if len(parts) == 5 and parts[0] == "v2":
        _, exp_raw, nonce, api_token, sig = parts
        try:
            exp = int(exp_raw)
        except ValueError:
            raise ValueError("invalid_session_token")

        payload = f"{exp}.{nonce}.{api_token}"
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

    if len(parts) != 4 or parts[0] != "v1":
        raise ValueError("invalid_session_token")

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
