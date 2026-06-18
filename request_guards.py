from __future__ import annotations

import logging

from fastapi import Request

from api_errors import ApiError
from security_rate_limit import RateLimitBackendUnavailable, check_rate_limit, get_request_identity


logger = logging.getLogger(__name__)


def request_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded
    client = request.client.host if request.client else None
    return client or "unknown"


def request_identity(request: Request, principal: str | None = None) -> str:
    return get_request_identity(request_ip(request), principal)


def apply_rate_limit(
    bucket: str,
    subject: str,
    *,
    limit: int,
    window_seconds: int,
    field: str = "rate_limit",
) -> None:
    try:
        decision = check_rate_limit(bucket, subject, limit=limit, window_seconds=window_seconds)
    except RateLimitBackendUnavailable:
        logger.error("rate_limit_backend_unavailable bucket=%s subject=%s", bucket, subject)
        raise ApiError(
            status_code=503,
            code="rate_limit_unavailable",
            message="Servico de limitacao indisponivel",
            field=field,
        )

    if decision.allowed:
        return

    logger.warning(
        "rate_limited bucket=%s subject=%s retry_after=%s",
        bucket,
        subject,
        decision.retry_after_seconds,
    )
    raise ApiError(
        status_code=429,
        code="rate_limited",
        message=f"Muitas tentativas. Aguarde {decision.retry_after_seconds}s e tente novamente.",
        field=field,
    )
