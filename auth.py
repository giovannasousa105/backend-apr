from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import SessionLocal
from models import User
from api_errors import ApiError
from auth_utils import resolve_api_token_from_session
from rbac import VALID_ROLES, ROLE_VISUALIZADOR, is_admin, normalize_role


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _extract_token(authorization: str | None, x_api_token: str | None) -> str | None:
    if authorization:
        value = authorization.strip()
        if value.lower().startswith("bearer "):
            return value.split(" ", 1)[1].strip()
    if x_api_token:
        return x_api_token.strip()
    return None


def get_current_user(
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

    user = db.execute(select(User).where(User.api_token == api_token)).scalar_one_or_none()
    if not user or not user.is_active:
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")
    normalized_role = normalize_role(user.role)
    user.role = normalized_role if normalized_role in VALID_ROLES else ROLE_VISUALIZADOR
    return user


def get_current_user_optional(
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

    user = db.execute(select(User).where(User.api_token == api_token)).scalar_one_or_none()
    if not user or not user.is_active:
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")
    normalized_role = normalize_role(user.role)
    user.role = normalized_role if normalized_role in VALID_ROLES else ROLE_VISUALIZADOR
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not is_admin(user.role):
        raise ApiError(status_code=403, code="forbidden", message="Acesso restrito a admin", field="role")
    return user
