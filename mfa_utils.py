from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import urllib.parse
from datetime import datetime, timezone


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _normalize_secret(secret: str) -> bytes:
    value = (secret or "").strip().replace(" ", "").upper()
    pad = "=" * (-len(value) % 8)
    return base64.b32decode(value + pad, casefold=True)


def _totp_code(secret: str, for_ts: int, *, digits: int = 6, step_seconds: int = 30) -> str:
    key = _normalize_secret(secret)
    counter = int(for_ts // step_seconds)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    )
    return str(code % (10**digits)).zfill(digits)


def verify_totp(secret: str, otp: str, *, window: int = 1, digits: int = 6, step_seconds: int = 30) -> bool:
    code = (otp or "").strip().replace(" ", "")
    if not code.isdigit() or len(code) != digits:
        return False
    now_ts = int(datetime.now(timezone.utc).timestamp())
    for delta in range(-window, window + 1):
        ts = now_ts + (delta * step_seconds)
        if hmac.compare_digest(_totp_code(secret, ts, digits=digits, step_seconds=step_seconds), code):
            return True
    return False


def build_otpauth_uri(secret: str, account_name: str, issuer: str | None = None) -> str:
    issuer_name = (issuer or os.getenv("MFA_ISSUER", "HCS")).strip() or "HCS"
    label = urllib.parse.quote(f"{issuer_name}:{account_name}")
    params = urllib.parse.urlencode(
        {
            "secret": secret,
            "issuer": issuer_name,
            "algorithm": "SHA1",
            "digits": "6",
            "period": "30",
        }
    )
    return f"otpauth://totp/{label}?{params}"


def generate_backup_codes(total: int = 8) -> list[str]:
    codes: list[str] = []
    for _ in range(total):
        left = secrets.token_hex(2).upper()
        right = secrets.token_hex(2).upper()
        codes.append(f"{left}-{right}")
    return codes


def _backup_secret() -> str:
    return (os.getenv("JWT_SECRET") or "").strip()


def hash_backup_code(code: str) -> str:
    normalized = (code or "").strip().upper()
    digest = hmac.new(
        _backup_secret().encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest
