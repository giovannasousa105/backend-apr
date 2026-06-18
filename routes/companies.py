from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api_errors import ApiError
from auth import get_current_user_optional, get_db
from auth_utils import generate_token, hash_password, issue_session_token, session_expires_at
from models import Company, User
from plan_utils import normalize_plan_name
from request_guards import apply_rate_limit, request_identity, request_ip
from rbac import ROLE_ADMIN
from security_audit import record_security_event, resolve_auth_session
from security_context import resolve_user_for_login, set_security_context
from session_security import register_session
from text_normalizer import normalize_text

router = APIRouter(prefix="/companies", tags=["Companies"])


class CompanyCreateRequest(BaseModel):
    name: str
    cnpj: str | None = None
    plan: str = "free"
    admin_name: str | None = None
    admin_email: str | None = None
    admin_password: str | None = Field(default=None, min_length=4)


class CompanyCreateResponse(BaseModel):
    token: str
    user: dict
    company: dict


def _build_user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "company_id": user.company_id,
        "company_name": user.company.name if user.company else None,
    }


def _extract_token(authorization: str | None, x_api_token: str | None) -> str | None:
    if authorization:
        value = authorization.strip()
        if value.lower().startswith("bearer "):
            return value.split(" ", 1)[1].strip()
    if x_api_token:
        return x_api_token.strip()
    return None


@router.post("", response_model=CompanyCreateResponse)
def create_company(
    payload: CompanyCreateRequest,
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    apply_rate_limit("company_create", request_identity(request, payload.admin_email or payload.name), limit=5, window_seconds=600)
    company_name = normalize_text(payload.name, keep_newlines=False, origin="user", field="name") or ""
    company_name = company_name.strip()
    if not company_name:
        raise ApiError(status_code=400, code="validation_error", message="Nome da empresa obrigatorio", field="name")

    existing_company = db.execute(select(Company).where(Company.name == company_name)).scalar_one_or_none()
    if existing_company:
        raise ApiError(status_code=409, code="conflict", message="Empresa ja cadastrada", field="name")

    cnpj = normalize_text(payload.cnpj, keep_newlines=False, origin="user", field="cnpj")
    if cnpj:
        existing_cnpj = db.execute(select(Company).where(Company.cnpj == cnpj)).scalar_one_or_none()
        if existing_cnpj:
            raise ApiError(status_code=409, code="conflict", message="CNPJ ja cadastrado", field="cnpj")

    plan_name = normalize_plan_name(payload.plan)
    company = Company(name=company_name, cnpj=cnpj, plan_name=plan_name)
    db.add(company)
    db.flush()
    bootstrap_user_id = current_user.id if current_user is not None else None
    bootstrap_role = current_user.role if current_user is not None else ROLE_ADMIN
    set_security_context(
        db,
        company_id=company.id,
        user_id=bootstrap_user_id,
        user_role=bootstrap_role,
        auth_bootstrap=True,
    )

    if current_user is not None:
        if current_user.company_id:
            raise ApiError(status_code=409, code="conflict", message="Usuario ja possui empresa", field="company_id")
        payload_email = (
            normalize_text(payload.admin_email, keep_newlines=False, origin="user", field="admin_email") or ""
        ).lower().strip()
        if payload_email and payload_email != current_user.email.lower():
            raise ApiError(
                status_code=400,
                code="validation_error",
                message="admin_email deve ser igual ao usuario autenticado",
                field="admin_email",
            )
        if payload.admin_name:
            current_user.name = normalize_text(payload.admin_name, keep_newlines=False, origin="user", field="admin_name")
        current_user.company_id = company.id
        current_user.role = ROLE_ADMIN
        if not current_user.api_token:
            current_user.api_token = generate_token()
        user = current_user
    else:
        email = (
            normalize_text(payload.admin_email, keep_newlines=False, origin="user", field="admin_email") or ""
        ).lower().strip()
        if not email:
            raise ApiError(
                status_code=400,
                code="validation_error",
                message="Email do admin obrigatorio",
                field="admin_email",
            )
        if not payload.admin_password:
            raise ApiError(
                status_code=400,
                code="missing_field",
                message="Senha do admin obrigatoria",
                field="admin_password",
            )
        existing_user = resolve_user_for_login(db, email)
        if existing_user:
            raise ApiError(status_code=409, code="conflict", message="Email do admin ja cadastrado", field="admin_email")
        admin_name = normalize_text(payload.admin_name, keep_newlines=False, origin="user", field="admin_name")
        user = User(
            email=email,
            name=admin_name,
            password_hash=hash_password(payload.admin_password),
            role=ROLE_ADMIN,
            company_id=company.id,
            api_token=generate_token(),
            is_active=True,
        )
        db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(company)
    set_security_context(db, company_id=company.id, user_id=user.id, user_role=user.role)
    token = issue_session_token(user.api_token)
    expires_at = session_expires_at(token)
    if not expires_at:
        raise ApiError(status_code=500, code="server_error", message="Falha ao gerar sessao", field="token")
    issued_session = register_session(
        db,
        user=user,
        token=token,
        expires_at=expires_at,
        ip_address=request.headers.get("x-forwarded-for") or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
    )
    actor = current_user or user
    current_session = resolve_auth_session(db, _extract_token(authorization, x_api_token))
    set_security_context(db, company_id=company.id, user_id=user.id, user_role=user.role)
    event_name = "admin_company_created" if current_user is not None else "admin_company_bootstrapped"
    record_security_event(
        db,
        user=actor,
        event=event_name,
        payload={
            "company_id": company.id,
            "company_name": company.name,
            "plan_name": company.plan_name,
            "admin_user_id": user.id,
        },
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        session=current_session if current_user is not None else issued_session,
    )
    db.commit()

    return {
        "token": token,
        "user": _build_user_payload(user),
        "company": {
            "id": company.id,
            "name": company.name,
            "cnpj": company.cnpj,
            "plan": company.plan,
            "created_at": company.created_at,
        },
    }
