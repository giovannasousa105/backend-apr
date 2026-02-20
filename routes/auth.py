from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from api_errors import ApiError
from auth import get_current_user, require_admin, get_db
from auth_utils import (
    generate_token,
    hash_password,
    issue_session_token,
    resolve_api_token_from_session,
    verify_password,
)
from models import User, Company
from plan_utils import DEFAULT_PLAN
from rbac import VALID_ROLES, normalize_role
from text_normalizer import normalize_text


router = APIRouter(prefix="/auth", tags=["Auth"])


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


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise ApiError(status_code=401, code="invalid_credentials", message="Credenciais invalidas", field="email")
    if not user.is_active:
        raise ApiError(status_code=403, code="inactive_user", message="Usuario inativo", field="email")
    return {"token": issue_session_token(user.api_token), "user": _user_out(user)}


@router.get("/me", response_model=AuthUserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    items = db.execute(select(Company).order_by(Company.name.asc())).scalars().all()
    return [CompanyOut(id=item.id, name=item.name, cnpj=item.cnpj) for item in items]


@router.post("/bootstrap", response_model=LoginResponse)
def bootstrap(payload: BootstrapRequest, db: Session = Depends(get_db)):
    total = db.execute(select(func.count()).select_from(User)).scalar_one()
    if total > 0:
        raise ApiError(status_code=409, code="conflict", message="Bootstrap ja realizado", field="user")

    company_name = normalize_text(payload.company, keep_newlines=False, origin="user", field="company") or ""
    company_cnpj = normalize_text(payload.cnpj, keep_newlines=False, origin="user", field="cnpj")
    company = Company(name=company_name.strip(), cnpj=company_cnpj, plan_name=DEFAULT_PLAN)
    db.add(company)
    db.flush()

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
    db.commit()
    db.refresh(user)
    return {"token": issue_session_token(user.api_token), "user": _user_out(user)}


@router.post("/refresh", response_model=LoginResponse)
def refresh_session(
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

    user = db.execute(select(User).where(User.api_token == api_token)).scalar_one_or_none()
    if not user or not user.is_active:
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="authorization")
    return {"token": issue_session_token(user.api_token), "user": _user_out(user)}


@router.post("/users", response_model=AuthUserOut)
def create_user(
    payload: CreateUserRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    role = normalize_role(payload.role)
    if role not in VALID_ROLES:
        raise ApiError(status_code=400, code="validation_error", message="Role invalido", field="role")

    email = payload.email.strip().lower()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
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
    db.commit()
    db.refresh(user)
    return _user_out(user)
