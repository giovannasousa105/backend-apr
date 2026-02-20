from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api_errors import ApiError
from auth import get_current_user, get_current_user_optional, get_db
from auth_utils import generate_token, hash_password, issue_session_token, verify_password
from invite_utils import (
    INVITE_STATUS_ACCEPTED,
    INVITE_STATUS_EXPIRED,
    INVITE_STATUS_PENDING,
    INVITE_STATUS_REVOKED,
    build_invite_link,
    default_invite_expiration,
    generate_invite_token,
    hash_invite_token,
    mask_email,
)
from models import Company, Invite, User
from rbac import ROLE_ADMIN, VALID_ROLES, normalize_role
from text_normalizer import normalize_text

router = APIRouter(prefix="/invites", tags=["Invites"])


class InviteCreateRequest(BaseModel):
    email: str
    role: str = Field(default="tecnico")


class InviteCreateResponse(BaseModel):
    id: int
    company_id: int
    email: str
    role: str
    status: str
    expires_at: datetime
    invite_link: str


class InviteVerifyResponse(BaseModel):
    valid: bool
    company_name: str
    email_masked: str
    role: str
    expires_at: datetime


class InviteAcceptRequest(BaseModel):
    token: str
    name: str | None = None
    password: str | None = Field(default=None, min_length=4)


class InviteAcceptResponse(BaseModel):
    token: str
    user: dict
    company: dict


def _ensure_admin(user: User) -> None:
    if normalize_role(user.role) != ROLE_ADMIN:
        raise ApiError(status_code=403, code="forbidden", message="Acesso restrito a admin", field="role")


def _expire_if_needed(invite: Invite, db: Session) -> Invite:
    if invite.status == INVITE_STATUS_PENDING and invite.expires_at <= datetime.utcnow():
        invite.status = INVITE_STATUS_EXPIRED
        db.commit()
        db.refresh(invite)
    return invite


def _load_pending_invite_by_token(raw_token: str, db: Session) -> Invite:
    token_hash = hash_invite_token(raw_token)
    invite = db.execute(select(Invite).where(Invite.token_hash == token_hash)).scalar_one_or_none()
    if not invite:
        raise ApiError(status_code=404, code="not_found", message="Convite nao encontrado", field="token")
    invite = _expire_if_needed(invite, db)
    if invite.status != INVITE_STATUS_PENDING:
        raise ApiError(status_code=400, code="invite_not_available", message="Convite indisponivel", field="token")
    return invite


def _build_user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": normalize_role(user.role),
        "company_id": user.company_id,
        "company_name": user.company.name if user.company else None,
    }


@router.post("", response_model=InviteCreateResponse)
def create_invite(
    payload: InviteCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    if not current_user.company_id:
        raise ApiError(status_code=403, code="forbidden", message="Usuario sem empresa vinculada", field="company_id")

    email = (normalize_text(payload.email, keep_newlines=False, origin="user", field="email") or "").lower().strip()
    if not email:
        raise ApiError(status_code=400, code="validation_error", message="Email obrigatorio", field="email")

    role = normalize_role(payload.role)
    if role not in VALID_ROLES:
        raise ApiError(status_code=400, code="validation_error", message="Role invalido", field="role")

    existing_pending = db.execute(
        select(Invite).where(
            Invite.company_id == current_user.company_id,
            Invite.email == email,
            Invite.status == INVITE_STATUS_PENDING,
        )
    ).scalar_one_or_none()
    if existing_pending:
        existing_pending = _expire_if_needed(existing_pending, db)
        if existing_pending.status == INVITE_STATUS_PENDING:
            raise ApiError(status_code=409, code="conflict", message="Ja existe convite pendente para este email", field="email")

    raw_token = generate_invite_token()
    invite = Invite(
        company_id=current_user.company_id,
        email=email,
        role=role,
        token_hash=hash_invite_token(raw_token),
        status=INVITE_STATUS_PENDING,
        expires_at=default_invite_expiration(),
        invited_by=current_user.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return {
        "id": invite.id,
        "company_id": invite.company_id,
        "email": invite.email,
        "role": invite.role,
        "status": invite.status,
        "expires_at": invite.expires_at,
        "invite_link": build_invite_link(raw_token),
    }


@router.get("", response_model=list[dict])
def list_invites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    stmt = (
        select(Invite)
        .where(Invite.company_id == current_user.company_id)
        .order_by(Invite.created_at.desc())
    )
    items = db.execute(stmt).scalars().all()
    out = []
    for item in items:
        item = _expire_if_needed(item, db)
        out.append(
            {
                "id": item.id,
                "email": item.email,
                "role": item.role,
                "status": item.status,
                "expires_at": item.expires_at,
                "created_at": item.created_at,
            }
        )
    return out


@router.post("/{invite_id}/revoke", response_model=dict)
def revoke_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    invite = db.get(Invite, invite_id)
    if not invite or invite.company_id != current_user.company_id:
        raise ApiError(status_code=404, code="not_found", message="Convite nao encontrado", field="invite_id")
    invite = _expire_if_needed(invite, db)
    if invite.status in {INVITE_STATUS_ACCEPTED, INVITE_STATUS_REVOKED}:
        return {"status": invite.status}
    invite.status = INVITE_STATUS_REVOKED
    invite.revoked_at = datetime.utcnow()
    db.commit()
    return {"status": invite.status}


@router.get("/verify", response_model=InviteVerifyResponse)
def verify_invite(
    token: str = Query(..., min_length=10),
    db: Session = Depends(get_db),
):
    invite = _load_pending_invite_by_token(token, db)
    company = db.get(Company, invite.company_id)
    if not company:
        raise ApiError(status_code=404, code="not_found", message="Empresa nao encontrada", field="company_id")
    return {
        "valid": True,
        "company_name": company.name,
        "email_masked": mask_email(invite.email),
        "role": invite.role,
        "expires_at": invite.expires_at,
    }


@router.post("/accept", response_model=InviteAcceptResponse)
def accept_invite(
    payload: InviteAcceptRequest,
    db: Session = Depends(get_db),
    maybe_user: User | None = Depends(get_current_user_optional),
):
    invite = _load_pending_invite_by_token(payload.token, db)
    company = db.get(Company, invite.company_id)
    if not company:
        raise ApiError(status_code=404, code="not_found", message="Empresa nao encontrada", field="company_id")

    accepted_user: User | None = None

    if maybe_user is not None:
        if maybe_user.email.lower() != invite.email.lower():
            raise ApiError(status_code=403, code="forbidden", message="Token de convite pertence a outro email", field="token")
        if maybe_user.company_id and maybe_user.company_id != invite.company_id:
            raise ApiError(status_code=409, code="conflict", message="Usuario ja vinculado a outra empresa", field="company_id")
        maybe_user.company_id = invite.company_id
        maybe_user.role = normalize_role(invite.role)
        accepted_user = maybe_user
    else:
        existing = db.execute(select(User).where(User.email == invite.email)).scalar_one_or_none()
        if existing:
            if not payload.password or not verify_password(payload.password, existing.password_hash):
                raise ApiError(status_code=401, code="invalid_credentials", message="Senha invalida para este email", field="password")
            if existing.company_id and existing.company_id != invite.company_id:
                raise ApiError(status_code=409, code="conflict", message="Usuario ja vinculado a outra empresa", field="company_id")
            existing.company_id = invite.company_id
            existing.role = normalize_role(invite.role)
            accepted_user = existing
        else:
            display_name = normalize_text(payload.name, keep_newlines=False, origin="user", field="name")
            if not payload.password:
                raise ApiError(status_code=400, code="missing_field", message="Senha obrigatoria para criar conta", field="password")
            accepted_user = User(
                email=invite.email,
                name=display_name,
                password_hash=hash_password(payload.password),
                role=normalize_role(invite.role),
                company_id=invite.company_id,
                api_token=generate_token(),
                is_active=True,
            )
            db.add(accepted_user)
            db.flush()

    invite.status = INVITE_STATUS_ACCEPTED
    invite.accepted_by = accepted_user.id if accepted_user else None
    invite.accepted_at = datetime.utcnow()
    db.commit()
    db.refresh(accepted_user)

    return {
        "token": issue_session_token(accepted_user.api_token),
        "user": _build_user_payload(accepted_user),
        "company": {
            "id": company.id,
            "name": company.name,
            "cnpj": company.cnpj,
            "plan": company.plan,
        },
    }
