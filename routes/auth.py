from __future__ import annotations

import os
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from api_errors import ApiError
from auth import get_current_user, require_admin, get_db
from auth_utils import (
    allow_legacy_api_tokens,
    generate_token,
    hash_password,
    issue_session_token,
    resolve_api_token_from_session,
    session_token_hash,
    session_expires_at,
    verify_password,
)
from mfa_utils import (
    build_otpauth_uri,
    generate_backup_codes,
    generate_totp_secret,
    hash_backup_code,
    verify_totp,
)
from models import User, Company, AuthSession, SecurityAuditEvent
from plan_utils import DEFAULT_PLAN
from request_guards import apply_rate_limit, request_identity, request_ip
from rbac import VALID_ROLES, normalize_role
from security_audit import parse_security_event_payload, record_security_event, resolve_auth_session
from security_rate_limit import (
    RateLimitBackendUnavailable,
    check_rate_limit,
    clear_rate_limit,
    clear_temporary_block,
    get_temporary_block,
    set_temporary_block,
)
from security_context import resolve_user_for_login, resolve_user_for_token, set_security_context
from session_security import register_session, require_refresh_session, revoke_all_user_sessions, revoke_session
from text_normalizer import normalize_text


router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


class AuthUserOut(BaseModel):
    id: int
    email: str
    name: str | None = None
    role: str
    company_id: int | None = None
    company_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=4)
    otp: str | None = None
    backup_code: str | None = None


class LoginResponse(BaseModel):
    token: str
    user: AuthUserOut


class BootstrapRequest(BaseModel):
    company: str
    cnpj: str | None = None
    email: str
    name: str | None = None
    password: str = Field(min_length=4)


class CreateUserRequest(BaseModel):
    email: str
    name: str | None = None
    password: str = Field(min_length=4)
    role: str = Field(default="tecnico")
    company_id: int | None = None
    company_name: str | None = None


class CompanyOut(BaseModel):
    id: int
    name: str
    cnpj: str | None = None


class LogoutResponse(BaseModel):
    revoked: bool


class SessionOut(BaseModel):
    id: int
    ip_address: str | None = None
    user_agent: str | None = None
    issued_at: datetime
    expires_at: datetime
    last_seen_at: datetime | None = None
    revoked_at: datetime | None = None
    is_current: bool = False


class MFASetupOut(BaseModel):
    secret: str
    otpauth_uri: str
    backup_codes: list[str]


class MFAStatusOut(BaseModel):
    enabled: bool


class SecurityEventOut(BaseModel):
    id: int
    event: str
    payload: dict[str, object]
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
    user_id: int | None = None
    user_email: str | None = None
    session_id: int | None = None
    previous_hash: str | None = None
    event_hash: str


class SecurityEventListOut(BaseModel):
    items: list[SecurityEventOut]
    next_cursor: int | None = None


def _user_out(user: User) -> AuthUserOut:
    role = normalize_role(user.role)
    if role not in VALID_ROLES:
        role = "tecnico"
    return AuthUserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=role,
        company_id=user.company_id,
        company_name=user.company.name if user.company else None,
    )


def _extract_token(authorization: str | None, x_api_token: str | None) -> str | None:
    if authorization:
        value = authorization.strip()
        if value.lower().startswith("bearer "):
            return value.split(" ", 1)[1].strip()
    if x_api_token:
        return x_api_token.strip()
    return None


def _auth_lock_window_seconds() -> int:
    return int(os.getenv("AUTH_LOGIN_FAILURE_WINDOW_SECONDS", "900"))


def _auth_lock_retry_after() -> int:
    return int(os.getenv("AUTH_LOGIN_LOCK_SECONDS", str(_auth_lock_window_seconds())))


def _raise_auth_locked(field: str, retry_after_seconds: int) -> None:
    raise ApiError(
        status_code=429,
        code="auth_locked",
        message=f"Muitas tentativas invalidas. Aguarde {retry_after_seconds}s e tente novamente.",
        field=field,
    )


def _temporary_block_retry_after(bucket: str, subject: str) -> int:
    try:
        return get_temporary_block(bucket, subject)
    except RateLimitBackendUnavailable:
        logger.error("temporary_block_backend_unavailable bucket=%s subject=%s", bucket, subject)
        raise ApiError(
            status_code=503,
            code="rate_limit_unavailable",
            message="Servico de limitacao indisponivel",
            field="rate_limit",
        )


def _ensure_login_not_locked(*subjects: str) -> None:
    retry_after = 0
    for subject in dict.fromkeys(item for item in subjects if item):
        retry_after = max(retry_after, _temporary_block_retry_after("auth_login_lock", subject))
    if retry_after > 0:
        _raise_auth_locked("email", retry_after)


def _register_failed_login(*subjects: str) -> None:
    limit = int(os.getenv("AUTH_LOGIN_FAILURE_LIMIT", "5"))
    window_seconds = _auth_lock_window_seconds()
    retry_after = _auth_lock_retry_after()
    should_lock = False
    unique_subjects = list(dict.fromkeys(item for item in subjects if item))

    for subject in unique_subjects:
        try:
            decision = check_rate_limit(
                "auth_login_fail",
                subject,
                limit=limit,
                window_seconds=window_seconds,
            )
        except RateLimitBackendUnavailable:
            logger.error("rate_limit_backend_unavailable bucket=auth_login_fail subject=%s", subject)
            raise ApiError(
                status_code=503,
                code="rate_limit_unavailable",
                message="Servico de limitacao indisponivel",
                field="rate_limit",
            )
        if not decision.allowed:
            should_lock = True
            retry_after = max(retry_after, decision.retry_after_seconds)

    if not should_lock:
        return

    for subject in unique_subjects:
        try:
            set_temporary_block("auth_login_lock", subject, ttl_seconds=retry_after)
        except RateLimitBackendUnavailable:
            logger.error("temporary_block_backend_unavailable bucket=auth_login_lock subject=%s", subject)
            raise ApiError(
                status_code=503,
                code="rate_limit_unavailable",
                message="Servico de limitacao indisponivel",
                field="rate_limit",
            )
    _raise_auth_locked("email", retry_after)


def _clear_failed_login_state(*subjects: str) -> None:
    unique_subjects = list(dict.fromkeys(item for item in subjects if item))
    for subject in unique_subjects:
        try:
            clear_rate_limit("auth_login_fail", subject, window_seconds=_auth_lock_window_seconds())
            clear_temporary_block("auth_login_lock", subject)
        except RateLimitBackendUnavailable:
            logger.warning("best_effort_clear_login_state_failed subject=%s", subject)


def _mfa_setup_summary_payload(
    *,
    backup_codes: list[str],
    regenerated: bool,
    mfa_enabled_before: bool,
) -> dict[str, object]:
    return {
        "regenerated": regenerated,
        "mfa_enabled_before": mfa_enabled_before,
        "backup_codes_count": len(backup_codes),
    }


def _auth_me_rate_limit() -> int:
    return int(os.getenv("AUTH_ME_RATE_LIMIT", "120"))


def _auth_users_rate_limit() -> int:
    return int(os.getenv("AUTH_USERS_RATE_LIMIT", "60"))


def _auth_admin_read_rate_limit() -> int:
    return int(os.getenv("AUTH_ADMIN_READ_RATE_LIMIT", "30"))


def _auth_session_read_rate_limit() -> int:
    return int(os.getenv("AUTH_SESSION_READ_RATE_LIMIT", "60"))


def _auth_session_write_rate_limit() -> int:
    return int(os.getenv("AUTH_SESSION_WRITE_RATE_LIMIT", "20"))


def _auth_security_events_rate_limit() -> int:
    return int(os.getenv("AUTH_SECURITY_EVENTS_RATE_LIMIT", "30"))


def _auth_logout_rate_limit() -> int:
    return int(os.getenv("AUTH_LOGOUT_RATE_LIMIT", "20"))


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    identity = request_identity(request, email)
    account_subject = f"acct:{email}" if email else ""
    apply_rate_limit("auth_login", identity, limit=int(os.getenv("AUTH_LOGIN_RATE_LIMIT", "8")), window_seconds=60)
    _ensure_login_not_locked(identity, account_subject)

    resolved_user = resolve_user_for_login(db, email)
    if not resolved_user or not verify_password(payload.password, resolved_user.password_hash):
        _register_failed_login(identity, account_subject)
        raise ApiError(status_code=401, code="invalid_credentials", message="Credenciais invalidas", field="email")
    if not resolved_user.is_active:
        _register_failed_login(identity, account_subject)
        raise ApiError(status_code=403, code="inactive_user", message="Usuario inativo", field="email")

    set_security_context(
        db,
        company_id=resolved_user.company_id,
        user_id=resolved_user.id,
        user_role=resolved_user.role,
    )
    user = db.get(User, resolved_user.id)
    if not user or not user.is_active:
        raise ApiError(status_code=401, code="invalid_credentials", message="Credenciais invalidas", field="email")

    used_backup_code = False
    if user.mfa_enabled:
        backup_hashes = set()
        if user.mfa_backup_codes_json:
            try:
                data = json.loads(user.mfa_backup_codes_json)
                if isinstance(data, list):
                    backup_hashes = {str(item).strip() for item in data if str(item).strip()}
            except Exception:
                backup_hashes = set()

        otp = (payload.otp or "").strip()
        backup_code = (payload.backup_code or "").strip()
        mfa_ok = False
        if user.mfa_secret and otp:
            mfa_ok = verify_totp(user.mfa_secret, otp)
        if not mfa_ok and backup_code and backup_hashes:
            backup_hash = hash_backup_code(backup_code)
            if backup_hash in backup_hashes:
                backup_hashes.remove(backup_hash)
                user.mfa_backup_codes_json = json.dumps(sorted(backup_hashes))
                mfa_ok = True
                used_backup_code = True
        if not mfa_ok:
            _register_failed_login(identity, account_subject)
            raise ApiError(status_code=401, code="mfa_required", message="Codigo MFA obrigatorio ou invalido", field="otp")

    token = issue_session_token(user.api_token)
    expires_at = session_expires_at(token)
    if not expires_at:
        raise ApiError(status_code=500, code="server_error", message="Falha ao gerar sessao", field="token")
    _clear_failed_login_state(identity, account_subject)
    current_session = register_session(
        db,
        user=user,
        token=token,
        expires_at=expires_at,
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    record_security_event(
        db,
        user=user,
        event="auth_login_succeeded",
        payload={
            "mfa_enabled": bool(user.mfa_enabled),
            "used_backup_code": used_backup_code,
            "session_expires_at": expires_at.isoformat(),
        },
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        session=current_session,
    )
    db.commit()
    return {"token": token, "user": _user_out(user)}


@router.get("/me", response_model=AuthUserOut)
def me(
    request: Request,
    user: User = Depends(get_current_user),
):
    apply_rate_limit("auth_me", request_identity(request, str(user.id)), limit=_auth_me_rate_limit(), window_seconds=60)
    return _user_out(user)


@router.get("/users", response_model=list[AuthUserOut])
def list_company_users(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    apply_rate_limit(
        "auth_users_list",
        request_identity(request, str(user.id)),
        limit=_auth_users_rate_limit(),
        window_seconds=60,
    )
    if not user.company_id:
        return []
    items = (
        db.execute(
            select(User)
            .where(User.company_id == user.company_id, User.is_active.is_(True))
            .order_by(func.coalesce(User.name, User.email).asc(), User.email.asc())
        )
        .scalars()
        .all()
    )
    return [_user_out(item) for item in items]


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    apply_rate_limit(
        "auth_companies_list",
        request_identity(request, str(admin.id)),
        limit=_auth_admin_read_rate_limit(),
        window_seconds=60,
    )
    items = db.execute(select(Company).order_by(Company.name.asc())).scalars().all()
    return [CompanyOut(id=item.id, name=item.name, cnpj=item.cnpj) for item in items]


@router.post("/bootstrap", response_model=LoginResponse)
def bootstrap(payload: BootstrapRequest, request: Request, db: Session = Depends(get_db)):
    identity = request_identity(request, payload.email)
    apply_rate_limit("auth_bootstrap", identity, limit=3, window_seconds=300)

    set_security_context(db, company_id=0, user_role="admin", auth_bootstrap=True)
    total = db.execute(select(func.count()).select_from(User)).scalar_one()
    if total > 0:
        raise ApiError(status_code=409, code="conflict", message="Bootstrap ja realizado", field="user")

    company_name = normalize_text(payload.company, keep_newlines=False, origin="user", field="company") or ""
    company_cnpj = normalize_text(payload.cnpj, keep_newlines=False, origin="user", field="cnpj")
    company = Company(name=company_name.strip(), cnpj=company_cnpj, plan_name=DEFAULT_PLAN)
    db.add(company)
    db.flush()
    set_security_context(db, company_id=company.id, user_role="admin", auth_bootstrap=True)

    user = User(
        email=payload.email.strip().lower(),
        name=normalize_text(payload.name, keep_newlines=False, origin="user", field="name"),
        password_hash=hash_password(payload.password),
        role="admin",
        company_id=company.id,
        api_token=generate_token(),
        is_active=True,
    )
    db.add(user)
    token = issue_session_token(user.api_token)
    expires_at = session_expires_at(token)
    if not expires_at:
        raise ApiError(status_code=500, code="server_error", message="Falha ao gerar sessao", field="token")
    db.flush()
    set_security_context(db, company_id=company.id, user_id=user.id, user_role=user.role)
    register_session(
        db,
        user=user,
        token=token,
        expires_at=expires_at,
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    db.refresh(user)
    return {"token": token, "user": _user_out(user)}


@router.post("/refresh", response_model=LoginResponse)
def refresh_session(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    db: Session = Depends(get_db),
):
    token = _extract_token(authorization, x_api_token)
    if not token:
        raise ApiError(status_code=401, code="auth_required", message="Token nao informado", field="authorization")
    try:
        api_token, _expired = resolve_api_token_from_session(token, allow_expired=True)
    except ValueError as exc:
        if str(exc) == "session_refresh_expired":
            raise ApiError(status_code=401, code="refresh_expired", message="Sessao expirada. Faca login novamente.", field="authorization")
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")

    identity = request_identity(request, api_token[-12:] if api_token else None)
    apply_rate_limit("auth_refresh", identity, limit=int(os.getenv("AUTH_REFRESH_RATE_LIMIT", "20")), window_seconds=60)

    can_rotate_current_session = True
    previous_session: AuthSession | None = None
    try:
        previous_session = require_refresh_session(db, token)
    except ValueError as exc:
        reason = str(exc)
        if reason == "session_refresh_expired":
            raise ApiError(status_code=401, code="refresh_expired", message="Sessao expirada. Faca login novamente.", field="authorization")
        if reason == "session_not_found":
            if allow_legacy_api_tokens():
                can_rotate_current_session = False
            else:
                raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")
        else:
            raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")

    resolved_user = resolve_user_for_token(db, api_token)
    if not resolved_user or not resolved_user.is_active:
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")

    set_security_context(
        db,
        company_id=resolved_user.company_id,
        user_id=resolved_user.id,
        user_role=resolved_user.role,
    )
    user = db.get(User, resolved_user.id)
    if not user or not user.is_active:
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")

    if can_rotate_current_session:
        revoke_session(db, token, reason="refresh_rotated")
    new_token = issue_session_token(user.api_token)
    expires_at = session_expires_at(new_token)
    if not expires_at:
        raise ApiError(status_code=500, code="server_error", message="Falha ao gerar sessao", field="token")
    new_session = register_session(
        db,
        user=user,
        token=new_token,
        expires_at=expires_at,
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    record_security_event(
        db,
        user=user,
        event="auth_session_refreshed",
        payload={
            "rotated_previous_session": bool(can_rotate_current_session),
            "previous_session_id": previous_session.id if previous_session else None,
            "new_session_expires_at": expires_at.isoformat(),
        },
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        session=new_session,
    )
    db.commit()
    return {"token": new_token, "user": _user_out(user)}


@router.post("/users", response_model=AuthUserOut)
def create_user(
    payload: CreateUserRequest,
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    identity = request_identity(request, str(admin.id))
    apply_rate_limit("auth_create_user", identity, limit=20, window_seconds=60)

    role = normalize_role(payload.role)
    if role not in VALID_ROLES:
        raise ApiError(status_code=400, code="validation_error", message="Role invalido", field="role")

    email = payload.email.strip().lower()
    existing = resolve_user_for_login(db, email)
    if existing:
        raise ApiError(status_code=409, code="conflict", message="Email ja cadastrado", field="email")

    company_id = payload.company_id or admin.company_id
    company = db.get(Company, company_id)
    if not company and payload.company_name:
        company_name = normalize_text(payload.company_name, keep_newlines=False, origin="user", field="company_name") or ""
        company_name = company_name.strip()
        company = db.execute(select(Company).where(Company.name == company_name)).scalar_one_or_none()
        if not company:
            company = Company(name=company_name, plan_name=DEFAULT_PLAN)
            db.add(company)
            db.flush()
        company_id = company.id
    if not company:
        raise ApiError(status_code=404, code="not_found", message="Empresa nao encontrada", field="company_id")

    user = User(
        email=email,
        name=normalize_text(payload.name, keep_newlines=False, origin="user", field="name"),
        password_hash=hash_password(payload.password),
        role=role,
        company_id=company_id,
        api_token=generate_token(),
        is_active=True,
    )
    db.add(user)
    db.flush()
    current_session = resolve_auth_session(db, _extract_token(authorization, x_api_token))
    record_security_event(
        db,
        user=admin,
        event="admin_user_created",
        payload={
            "created_user_id": user.id,
            "created_user_email": user.email,
            "created_user_role": user.role,
            "company_id": user.company_id,
        },
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        session=current_session,
    )
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/logout", response_model=LogoutResponse)
def logout_current_session(
    request: Request,
    response: Response,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    token = _extract_token(authorization, x_api_token)
    if not token:
        raise ApiError(status_code=401, code="auth_required", message="Token nao informado", field="authorization")
    token_subject = session_token_hash(token)[-12:]
    apply_rate_limit(
        "auth_logout",
        request_identity(request, token_subject),
        limit=_auth_logout_rate_limit(),
        window_seconds=60,
    )
    current_session = resolve_auth_session(db, token)
    actor = db.get(User, current_session.user_id) if current_session else None
    revoked = revoke_session(db, token, reason="logout")
    if actor and revoked:
        record_security_event(
            db,
            user=actor,
            event="auth_session_logout_current",
            payload={"revoked": True, "session_id": current_session.id if current_session else None},
            ip_address=request_ip(request),
            user_agent=request.headers.get("user-agent"),
            session=current_session,
        )
    db.commit()
    response.headers["cache-control"] = "no-store"
    return LogoutResponse(revoked=bool(revoked))


@router.post("/logout-all", response_model=dict)
def logout_all_sessions(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    apply_rate_limit(
        "auth_logout_all",
        request_identity(request, str(user.id)),
        limit=_auth_session_write_rate_limit(),
        window_seconds=60,
    )
    current_session = resolve_auth_session(db, _extract_token(authorization, x_api_token))
    count = revoke_all_user_sessions(db, user_id=user.id, reason="logout_all")
    record_security_event(
        db,
        user=user,
        event="auth_session_logout_all",
        payload={"revoked_sessions": int(count)},
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        session=current_session,
    )
    db.commit()
    return {"revoked_sessions": int(count)}


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionOut]:
    apply_rate_limit(
        "auth_sessions_list",
        request_identity(request, str(user.id)),
        limit=_auth_session_read_rate_limit(),
        window_seconds=60,
    )
    current_token = _extract_token(authorization, x_api_token) or ""
    current_hash = ""
    if current_token:
        current_hash = session_token_hash(current_token)

    items = (
        db.execute(select(AuthSession).where(AuthSession.user_id == user.id).order_by(AuthSession.issued_at.desc()))
        .scalars()
        .all()
    )
    out: list[SessionOut] = []
    for item in items:
        out.append(
            SessionOut(
                id=item.id,
                ip_address=item.ip_address,
                user_agent=item.user_agent,
                issued_at=item.issued_at,
                expires_at=item.expires_at,
                last_seen_at=item.last_seen_at,
                revoked_at=item.revoked_at,
                is_current=(item.token_hash == current_hash),
            )
        )
    return out


@router.get("/security-events", response_model=SecurityEventListOut)
def list_security_events(
    request: Request,
    limit: int = 80,
    cursor_id: int | None = None,
    event: str | None = None,
    actor_user_id: int | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SecurityEventListOut:
    apply_rate_limit(
        "auth_security_events_list",
        request_identity(request, str(admin.id)),
        limit=_auth_security_events_rate_limit(),
        window_seconds=60,
    )
    if not admin.company_id:
        return SecurityEventListOut(items=[], next_cursor=None)

    page_limit = max(1, min(int(limit), 200))
    stmt = select(SecurityAuditEvent).where(SecurityAuditEvent.company_id == admin.company_id)
    if cursor_id and cursor_id > 0:
        stmt = stmt.where(SecurityAuditEvent.id < cursor_id)
    if actor_user_id and actor_user_id > 0:
        stmt = stmt.where(SecurityAuditEvent.user_id == actor_user_id)
    if event:
        normalized_event = event.strip()[:80]
        if normalized_event:
            stmt = stmt.where(SecurityAuditEvent.event == normalized_event)
    stmt = stmt.order_by(SecurityAuditEvent.id.desc()).limit(page_limit + 1)
    rows = db.execute(stmt).scalars().all()
    has_more = len(rows) > page_limit
    items = rows[:page_limit]

    user_ids = {item.user_id for item in items if item.user_id is not None}
    email_by_id: dict[int, str] = {}
    if user_ids:
        for user_id, user_email in db.execute(
            select(User.id, User.email).where(User.id.in_(user_ids))
        ).all():
            email_by_id[int(user_id)] = str(user_email)

    out: list[SecurityEventOut] = []
    for item in items:
        out.append(
            SecurityEventOut(
                id=item.id,
                event=item.event,
                payload=parse_security_event_payload(item.payload),
                ip_address=item.ip_address,
                user_agent=item.user_agent,
                created_at=item.created_at,
                user_id=item.user_id,
                user_email=email_by_id.get(item.user_id) if item.user_id else None,
                session_id=item.session_id,
                previous_hash=item.previous_hash,
                event_hash=item.event_hash,
            )
        )

    next_cursor = items[-1].id if has_more and items else None
    return SecurityEventListOut(items=out, next_cursor=next_cursor)


@router.post("/sessions/{session_id}/revoke", response_model=LogoutResponse)
def revoke_session_by_id(
    session_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    apply_rate_limit(
        "auth_session_revoke",
        request_identity(request, str(user.id)),
        limit=_auth_session_write_rate_limit(),
        window_seconds=60,
    )
    session = db.get(AuthSession, session_id)
    if not session or session.user_id != user.id:
        raise ApiError(status_code=404, code="not_found", message="Sessao nao encontrada", field="session_id")
    if session.revoked_at is None:
        session.revoked_at = datetime.utcnow()
        session.revoke_reason = "manual_revoke"
    current_session = resolve_auth_session(db, _extract_token(authorization, x_api_token))
    record_security_event(
        db,
        user=user,
        event="auth_session_revoked_by_user",
        payload={"target_session_id": session.id, "target_user_id": session.user_id},
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        session=current_session,
    )
    db.commit()
    return LogoutResponse(revoked=True)


@router.get("/mfa/status", response_model=MFAStatusOut)
def mfa_status(request: Request, user: User = Depends(get_current_user)) -> MFAStatusOut:
    apply_rate_limit(
        "auth_mfa_status",
        request_identity(request, str(user.id)),
        limit=_auth_me_rate_limit(),
        window_seconds=60,
    )
    return MFAStatusOut(enabled=bool(user.mfa_enabled))


@router.post("/mfa/setup", response_model=MFASetupOut)
def mfa_setup(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MFASetupOut:
    apply_rate_limit("auth_mfa_setup", request_identity(request, str(user.id)), limit=5, window_seconds=300)
    current_token = _extract_token(authorization, x_api_token)
    current_session = resolve_auth_session(db, current_token)
    had_existing_setup = bool(user.mfa_secret or user.mfa_backup_codes_json)
    mfa_enabled_before = bool(user.mfa_enabled)
    secret = generate_totp_secret()
    backup_codes = generate_backup_codes()
    user.mfa_secret = secret
    user.mfa_enabled = False
    user.mfa_backup_codes_json = json.dumps([hash_backup_code(code) for code in backup_codes])
    event_name = "mfa_secret_regenerated" if had_existing_setup else "mfa_secret_created"
    record_security_event(
        db,
        user=user,
        event=event_name,
        payload=_mfa_setup_summary_payload(
            backup_codes=backup_codes,
            regenerated=had_existing_setup,
            mfa_enabled_before=mfa_enabled_before,
        ),
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        session=current_session,
    )
    db.commit()
    db.refresh(user)
    return MFASetupOut(
        secret=secret,
        otpauth_uri=build_otpauth_uri(secret, user.email),
        backup_codes=backup_codes,
    )


class MFABackupCodesExportedOut(BaseModel):
    recorded: bool


@router.post("/mfa/backup-codes/exported", response_model=MFABackupCodesExportedOut)
def mfa_backup_codes_exported(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MFABackupCodesExportedOut:
    current_token = _extract_token(authorization, x_api_token)
    current_session = resolve_auth_session(db, current_token)
    apply_rate_limit("auth_mfa_backup_exported", request_identity(request, str(user.id)), limit=10, window_seconds=300)
    backup_code_hashes: list[str] = []
    if user.mfa_backup_codes_json:
        try:
            parsed = json.loads(user.mfa_backup_codes_json)
            if isinstance(parsed, list):
                backup_code_hashes = [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            backup_code_hashes = []
    if not backup_code_hashes:
        raise ApiError(status_code=400, code="mfa_not_setup", message="Backup codes indisponiveis", field="mfa")
    record_security_event(
        db,
        user=user,
        event="mfa_backup_codes_exported",
        payload={
            "delivery": "txt_download",
            "mfa_enabled": bool(user.mfa_enabled),
            "backup_codes_remaining": len(backup_code_hashes),
        },
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        session=current_session,
    )
    db.commit()
    return MFABackupCodesExportedOut(recorded=True)


class MFAEnableRequest(BaseModel):
    otp: str = Field(min_length=6, max_length=8)


@router.post("/mfa/enable", response_model=MFAStatusOut)
def mfa_enable(
    payload: MFAEnableRequest,
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MFAStatusOut:
    apply_rate_limit("auth_mfa_enable", request_identity(request, str(user.id)), limit=10, window_seconds=300)
    if not user.mfa_secret:
        raise ApiError(status_code=400, code="mfa_not_setup", message="MFA nao configurado", field="mfa")
    if not verify_totp(user.mfa_secret, payload.otp):
        raise ApiError(status_code=400, code="invalid_mfa_code", message="Codigo MFA invalido", field="otp")
    user.mfa_enabled = True
    current_session = resolve_auth_session(db, _extract_token(authorization, x_api_token))
    record_security_event(
        db,
        user=user,
        event="mfa_enabled",
        payload={"method": "totp"},
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        session=current_session,
    )
    db.commit()
    return MFAStatusOut(enabled=True)


class MFADisableRequest(BaseModel):
    password: str = Field(min_length=4)
    otp: str = Field(min_length=6, max_length=8)


@router.post("/mfa/disable", response_model=MFAStatusOut)
def mfa_disable(
    payload: MFADisableRequest,
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MFAStatusOut:
    apply_rate_limit("auth_mfa_disable", request_identity(request, str(user.id)), limit=5, window_seconds=300)
    if not verify_password(payload.password, user.password_hash):
        raise ApiError(status_code=401, code="invalid_credentials", message="Credenciais invalidas", field="password")
    if user.mfa_enabled and user.mfa_secret and not verify_totp(user.mfa_secret, payload.otp):
        raise ApiError(status_code=400, code="invalid_mfa_code", message="Codigo MFA invalido", field="otp")
    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes_json = None
    current_session = resolve_auth_session(db, _extract_token(authorization, x_api_token))
    record_security_event(
        db,
        user=user,
        event="mfa_disabled",
        payload={"method": "totp"},
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        session=current_session,
    )
    db.commit()
    return MFAStatusOut(enabled=False)
