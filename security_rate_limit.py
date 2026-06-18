from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from functools import lru_cache

from redis import Redis


@dataclass
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class RateLimitBackendUnavailable(RuntimeError):
    pass


class _InMemoryLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, tuple[int, int]] = {}

    def hit(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = int(time.time())
        window_start = now - (now % window_seconds)
        expires_at = window_start + window_seconds
        with self._lock:
            count, stored_expires = self._store.get(key, (0, expires_at))
            if stored_expires <= now:
                count = 0
                stored_expires = expires_at
            count += 1
            self._store[key] = (count, stored_expires)
        retry_after = max(1, stored_expires - now)
        return RateLimitDecision(allowed=count <= limit, retry_after_seconds=retry_after)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)


class _InMemoryTemporaryBlocks:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, int] = {}

    def set(self, key: str, ttl_seconds: int) -> None:
        expires_at = int(time.time()) + max(1, ttl_seconds)
        with self._lock:
            self._store[key] = expires_at

    def retry_after(self, key: str) -> int:
        now = int(time.time())
        with self._lock:
            expires_at = self._store.get(key)
            if not expires_at:
                return 0
            if expires_at <= now:
                self._store.pop(key, None)
                return 0
            return max(1, expires_at - now)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)


_memory_limiter = _InMemoryLimiter()
_memory_blocks = _InMemoryTemporaryBlocks()


@lru_cache(maxsize=1)
def _redis_client() -> Redis | None:
    redis_url = (os.getenv("REDIS_URL") or "").strip()
    if not redis_url:
        return None
    try:
        return Redis.from_url(redis_url, decode_responses=True, socket_timeout=0.5)
    except Exception:
        return None


def _redis_hit(key: str, limit: int, window_seconds: int) -> RateLimitDecision:
    now = int(time.time())
    ttl = max(1, window_seconds - (now % window_seconds))
    client = _redis_client()
    strict = os.getenv("RATE_LIMIT_REDIS_REQUIRED", "false").strip().lower() in {"1", "true", "yes"}
    if client is None:
        if strict:
            raise RateLimitBackendUnavailable("redis_unavailable")
        return _memory_limiter.hit(key, limit, window_seconds)
    try:
        count = client.incr(key)
        if count == 1:
            client.expire(key, ttl + 1)
        return RateLimitDecision(allowed=count <= limit, retry_after_seconds=ttl)
    except Exception:
        if strict:
            raise RateLimitBackendUnavailable("redis_unreachable")
        return _memory_limiter.hit(key, limit, window_seconds)


def _strict_mode_enabled() -> bool:
    return os.getenv("RATE_LIMIT_REDIS_REQUIRED", "false").strip().lower() in {"1", "true", "yes"}


def _rate_limit_key(bucket: str, subject: str, window_seconds: int) -> str:
    now = int(time.time())
    window = now // window_seconds
    return f"rl:{bucket}:{subject}:{window}"


def _temporary_block_key(bucket: str, subject: str) -> str:
    return f"tmp_block:{bucket}:{subject}"


def check_rate_limit(bucket: str, subject: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
    key = _rate_limit_key(bucket, subject, window_seconds)
    return _redis_hit(key, limit, window_seconds)


def ensure_rate_limit_backend() -> None:
    strict = _strict_mode_enabled()
    if not strict:
        return
    client = _redis_client()
    if client is None:
        raise RuntimeError("RATE_LIMIT_REDIS_REQUIRED=true, mas REDIS_URL nao esta configurada")
    try:
        client.ping()
    except Exception as exc:
        raise RuntimeError("RATE_LIMIT_REDIS_REQUIRED=true, mas Redis nao esta acessivel") from exc


def clear_rate_limit(bucket: str, subject: str, *, window_seconds: int) -> None:
    key = _rate_limit_key(bucket, subject, window_seconds)
    client = _redis_client()
    strict = _strict_mode_enabled()
    if client is None:
        if strict:
            raise RateLimitBackendUnavailable("redis_unavailable")
        _memory_limiter.delete(key)
        return
    try:
        client.delete(key)
    except Exception:
        if strict:
            raise RateLimitBackendUnavailable("redis_unreachable")
        _memory_limiter.delete(key)


def set_temporary_block(bucket: str, subject: str, *, ttl_seconds: int) -> None:
    key = _temporary_block_key(bucket, subject)
    ttl = max(1, int(ttl_seconds))
    client = _redis_client()
    strict = _strict_mode_enabled()
    if client is None:
        if strict:
            raise RateLimitBackendUnavailable("redis_unavailable")
        _memory_blocks.set(key, ttl)
        return
    try:
        client.set(key, "1", ex=ttl)
    except Exception:
        if strict:
            raise RateLimitBackendUnavailable("redis_unreachable")
        _memory_blocks.set(key, ttl)


def get_temporary_block(bucket: str, subject: str) -> int:
    key = _temporary_block_key(bucket, subject)
    client = _redis_client()
    strict = _strict_mode_enabled()
    if client is None:
        if strict:
            raise RateLimitBackendUnavailable("redis_unavailable")
        return _memory_blocks.retry_after(key)
    try:
        ttl = client.ttl(key)
        if ttl is None or ttl < 0:
            return 0
        return int(ttl)
    except Exception:
        if strict:
            raise RateLimitBackendUnavailable("redis_unreachable")
        return _memory_blocks.retry_after(key)


def clear_temporary_block(bucket: str, subject: str) -> None:
    key = _temporary_block_key(bucket, subject)
    client = _redis_client()
    strict = _strict_mode_enabled()
    if client is None:
        if strict:
            raise RateLimitBackendUnavailable("redis_unavailable")
        _memory_blocks.delete(key)
        return
    try:
        client.delete(key)
    except Exception:
        if strict:
            raise RateLimitBackendUnavailable("redis_unreachable")
        _memory_blocks.delete(key)


def get_request_identity(ip_address: str | None, principal: str | None = None) -> str:
    ip = (ip_address or "unknown").strip()
    if "," in ip:
        ip = ip.split(",", 1)[0].strip()
    principal_norm = (principal or "").strip().lower()
    if principal_norm:
        return f"{ip}|{principal_norm}"
    return ip
