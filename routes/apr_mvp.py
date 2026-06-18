from __future__ import annotations

import json
from datetime import date as calendar_date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api_errors import ApiError
from auth import get_current_user, get_db
from models import APR, APREvent, User
from rbac import can_write, normalize_role
from status_utils import normalize_status
from text_normalizer import normalize_text
from norm_profile_service import apply_profile_snapshot_to_apr, resolve_norm_profile
from request_guards import apply_rate_limit, request_identity

router = APIRouter(prefix="/aprs", tags=["APR MVP"])

_STORAGE_STATUS = {
    "draft": "rascunho",
    "submitted": "enviado",
    "approved": "aprovado",
    "rejected": "reprovado",
    "archived": "arquivado",
}


class AprMvpCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    location: str | None = None
    activity: str | None = None
    date: calendar_date | None = None
    hazards: list[dict[str, Any]] = Field(default_factory=list)
    controls: list[dict[str, Any]] = Field(default_factory=list)


class AprMvpUpdateRequest(BaseModel):
    title: str | None = None
    location: str | None = None
    activity: str | None = None
    date: calendar_date | None = None
    hazards: list[dict[str, Any]] | None = None
    controls: list[dict[str, Any]] | None = None


class AprMvpSubmitResponse(BaseModel):
    id: str
    status: str
    submitted_at: datetime


class AprMvpOut(BaseModel):
    id: str
    code: str
    company_id: int
    created_by: int | None = None
    title: str
    location: str | None = None
    activity: str | None = None
    date: calendar_date | None = None
    contract_id: str | None = None
    unit_id: str | None = None
    norm_profile_id: int | None = None
    norm_profile_version: int | None = None
    norm_profile_mode: str | None = None
    hazards: list[dict[str, Any]]
    controls: list[dict[str, Any]]
    status: str
    current_stage: str
    approved_by_user_id: int | None = None
    approved_by_name: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


def _build_apr_code(apr: APR) -> str:
    if apr.id is not None and apr.id > 0:
        return f"APR-{apr.id:06d}"
    fallback = (apr.external_id or "").replace("-", "").upper()
    if fallback:
        return f"APR-{fallback[:6]}"
    return "APR-000000"


def _to_public_status(status: str | None) -> str:
    normalized = normalize_status(status)
    if normalized == "draft":
        return "draft"
    if normalized == "submitted":
        return "submitted"
    if normalized in {"approved", "final"}:
        return "approved"
    if normalized == "rejected":
        return "rejected"
    if normalized == "archived":
        return "archived"
    return "draft"


def _to_storage_status(status: str) -> str:
    key = normalize_status(status)
    if key not in _STORAGE_STATUS:
        raise ApiError(status_code=400, code="validation_error", message="Status invalido", field="status")
    return _STORAGE_STATUS[key]


def _serialize(apr: APR) -> AprMvpOut:
    return AprMvpOut(
        id=apr.external_id or str(apr.id),
        code=_build_apr_code(apr),
        company_id=apr.company_id or 0,
        created_by=apr.user_id,
        title=apr.titulo,
        location=apr.worksite,
        activity=apr.descricao,
        date=apr.date,
        contract_id=apr.contract_id,
        unit_id=apr.unit_id,
        norm_profile_id=apr.norm_profile_id,
        norm_profile_version=apr.norm_profile_version,
        norm_profile_mode=apr.norm_profile_mode,
        hazards=apr.hazards,
        controls=apr.controls,
        status=_to_public_status(apr.status),
        current_stage=apr.current_stage or "criar",
        approved_by_user_id=apr.approved_by_user_id,
        approved_by_name=apr.approved_by_name,
        approved_at=apr.approved_at,
        created_at=apr.criado_em,
        updated_at=apr.atualizado_em,
    )


def _ensure_write_access(user: User) -> None:
    if not can_write(normalize_role(user.role)):
        raise ApiError(status_code=403, code="forbidden", message="Perfil sem permissao de escrita", field="role")


def _add_event(db: Session, apr: APR, event: str, payload: dict[str, Any], actor: User) -> None:
    with_actor = dict(payload)
    with_actor["actor"] = {
        "id": actor.id,
        "email": actor.email,
        "name": actor.name,
        "role": normalize_role(actor.role),
    }
    db.add(
        APREvent(
            apr_id=apr.id,
            company_id=apr.company_id,
            event=event,
            payload=json.dumps(with_actor, ensure_ascii=False),
        )
    )


def _get_apr_or_404(apr_id: str, db: Session) -> APR:
    apr = db.execute(select(APR).where(APR.external_id == apr_id)).scalar_one_or_none()
    if not apr:
        legacy_id = int(apr_id) if apr_id.isdigit() else None
        if legacy_id is not None:
            apr = db.get(APR, legacy_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="id")
    return apr


def _ensure_same_company(apr: APR, user: User) -> None:
    if not user.company_id:
        raise ApiError(status_code=403, code="forbidden", message="Usuario sem empresa vinculada", field="company_id")
    if apr.company_id != user.company_id:
        raise ApiError(status_code=403, code="forbidden", message="Acesso negado", field="id")


def _apr_mvp_identity(request: Request, user: User, resource: str | None = None) -> str:
    principal = str(user.id)
    if resource:
        principal = f"{user.id}:{resource}"
    return request_identity(request, principal)


@router.post("", response_model=AprMvpOut)
def create_apr(
    payload: AprMvpCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("apr_mvp_create", _apr_mvp_identity(request, current_user), limit=30, window_seconds=60)
    _ensure_write_access(current_user)
    if not current_user.company_id:
        raise ApiError(status_code=403, code="forbidden", message="Usuario sem empresa vinculada", field="company_id")

    title = normalize_text(payload.title, keep_newlines=False, origin="user", field="title") or ""
    if not title.strip():
        raise ApiError(status_code=400, code="validation_error", message="title obrigatorio", field="title")
    location = normalize_text(payload.location, keep_newlines=False, origin="user", field="location")
    activity = normalize_text(payload.activity, keep_newlines=True, origin="user", field="activity")

    apr = APR(
        titulo=title.strip(),
        risco="mvp",
        descricao=activity,
        worksite=location,
        sector=location,
        date=payload.date,
        company_id=current_user.company_id,
        user_id=current_user.id,
        status=_to_storage_status("draft"),
        current_stage="criar",
    )
    profile, resolved_from = resolve_norm_profile(
        db,
        company_id=int(current_user.company_id),
        actor_user_id=current_user.id,
    )
    apply_profile_snapshot_to_apr(apr, profile, resolved_from=resolved_from)
    apr.hazards = payload.hazards
    apr.controls = payload.controls

    db.add(apr)
    db.commit()
    db.refresh(apr)
    _add_event(db, apr, "created_mvp", {"status": "draft"}, current_user)
    db.commit()
    return _serialize(apr)


@router.get("", response_model=list[AprMvpOut])
def list_aprs(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.company_id:
        return []
    stmt = select(APR).where(APR.company_id == current_user.company_id)
    if not include_archived:
        stmt = stmt.where(APR.status != _STORAGE_STATUS["archived"])
    rows = (
        db.execute(
            stmt.order_by(APR.criado_em.desc())
        )
        .scalars()
        .all()
    )
    return [_serialize(item) for item in rows]


@router.get("/{apr_id}", response_model=AprMvpOut)
def get_apr(
    apr_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apr = _get_apr_or_404(apr_id, db)
    _ensure_same_company(apr, current_user)
    return _serialize(apr)


@router.put("/{apr_id}", response_model=AprMvpOut)
def update_apr(
    apr_id: str,
    payload: AprMvpUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("apr_mvp_update", _apr_mvp_identity(request, current_user, apr_id), limit=60, window_seconds=60)
    _ensure_write_access(current_user)
    apr = _get_apr_or_404(apr_id, db)
    _ensure_same_company(apr, current_user)

    current_status = _to_public_status(apr.status)
    if current_status in {"submitted", "approved", "archived"}:
        raise ApiError(
            status_code=400,
            code="apr_not_editable",
            message="APR no estado atual nao pode ser modificada",
            field="status",
        )

    changed: dict[str, Any] = {}
    if payload.title is not None:
        title = normalize_text(payload.title, keep_newlines=False, origin="user", field="title") or ""
        if not title.strip():
            raise ApiError(status_code=400, code="validation_error", message="title obrigatorio", field="title")
        apr.titulo = title.strip()
        changed["title"] = True
    if payload.location is not None:
        loc = normalize_text(payload.location, keep_newlines=False, origin="user", field="location")
        apr.worksite = loc
        apr.sector = loc
        changed["location"] = True
    if payload.activity is not None:
        apr.descricao = normalize_text(payload.activity, keep_newlines=True, origin="user", field="activity")
        changed["activity"] = True
    if payload.date is not None:
        apr.date = payload.date
        changed["date"] = True
    if payload.hazards is not None:
        apr.hazards = payload.hazards
        changed["hazards"] = True
    if payload.controls is not None:
        apr.controls = payload.controls
        changed["controls"] = True

    if apr.norm_profile_id is None:
        profile, resolved_from = resolve_norm_profile(
            db,
            company_id=int(current_user.company_id),
            actor_user_id=current_user.id,
        )
        apply_profile_snapshot_to_apr(apr, profile, resolved_from=resolved_from)
        changed["norm_profile"] = True

    db.commit()
    db.refresh(apr)
    if changed:
        _add_event(db, apr, "updated_mvp", changed, current_user)
        db.commit()
    return _serialize(apr)


@router.delete("/{apr_id}", response_model=dict)
def delete_apr(
    apr_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("apr_mvp_delete", _apr_mvp_identity(request, current_user, apr_id), limit=20, window_seconds=60)
    _ensure_write_access(current_user)
    apr = _get_apr_or_404(apr_id, db)
    _ensure_same_company(apr, current_user)

    current_status = _to_public_status(apr.status)
    if current_status == "archived":
        return {"status": "ok", "id": apr.external_id or str(apr.id), "archived": True}

    apr.status = _to_storage_status("archived")
    apr.current_stage = "relatorio"
    db.commit()
    db.refresh(apr)
    _add_event(
        db,
        apr,
        "deleted_mvp",
        {"mode": "soft_delete", "status": "archived", "from": current_status},
        current_user,
    )
    db.commit()
    return {"status": "ok", "id": apr.external_id or str(apr.id), "archived": True}


@router.post("/{apr_id}/submit", response_model=AprMvpSubmitResponse)
def submit_apr(
    apr_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("apr_mvp_submit", _apr_mvp_identity(request, current_user, apr_id), limit=20, window_seconds=60)
    _ensure_write_access(current_user)
    apr = _get_apr_or_404(apr_id, db)
    _ensure_same_company(apr, current_user)
    current_status = _to_public_status(apr.status)
    if current_status not in {"draft", "rejected"}:
        raise ApiError(
            status_code=400,
            code="invalid_status_transition",
            message="Somente APR em draft/rejected pode ser enviada",
            field="status",
        )
    apr.status = _to_storage_status("submitted")
    apr.current_stage = "aprovacao"
    db.commit()
    db.refresh(apr)
    _add_event(db, apr, "submitted_mvp", {"from": current_status, "to": "submitted"}, current_user)
    db.commit()
    return {
        "id": apr.external_id,
        "status": "submitted",
        "submitted_at": apr.atualizado_em,
    }
