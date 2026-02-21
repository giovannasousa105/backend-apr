from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api_errors import ApiError
from auth import get_current_user, get_db
from models import APR, APREvent, User
from rbac import can_write, normalize_role
from status_utils import normalize_status
from text_normalizer import normalize_text

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
    hazards: list[dict[str, Any]] = Field(default_factory=list)
    controls: list[dict[str, Any]] = Field(default_factory=list)


class AprMvpUpdateRequest(BaseModel):
    title: str | None = None
    location: str | None = None
    activity: str | None = None
    hazards: list[dict[str, Any]] | None = None
    controls: list[dict[str, Any]] | None = None


class AprMvpSubmitResponse(BaseModel):
    id: str
    status: str
    submitted_at: datetime


class AprMvpOut(BaseModel):
    id: str
    company_id: int
    created_by: int | None = None
    title: str
    location: str | None = None
    activity: str | None = None
    hazards: list[dict[str, Any]]
    controls: list[dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime


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
        company_id=apr.company_id or 0,
        created_by=apr.user_id,
        title=apr.titulo,
        location=apr.worksite,
        activity=apr.descricao,
        hazards=apr.hazards,
        controls=apr.controls,
        status=_to_public_status(apr.status),
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


@router.post("", response_model=AprMvpOut)
def create_apr(
    payload: AprMvpCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
        company_id=current_user.company_id,
        user_id=current_user.id,
        status=_to_storage_status("draft"),
    )
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.company_id:
        return []
    rows = (
        db.execute(
            select(APR)
            .where(APR.company_id == current_user.company_id)
            .order_by(APR.criado_em.desc())
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    if payload.hazards is not None:
        apr.hazards = payload.hazards
        changed["hazards"] = True
    if payload.controls is not None:
        apr.controls = payload.controls
        changed["controls"] = True

    db.commit()
    db.refresh(apr)
    if changed:
        _add_event(db, apr, "updated_mvp", changed, current_user)
        db.commit()
    return _serialize(apr)


@router.post("/{apr_id}/submit", response_model=AprMvpSubmitResponse)
def submit_apr(
    apr_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    db.commit()
    db.refresh(apr)
    _add_event(db, apr, "submitted_mvp", {"from": current_status, "to": "submitted"}, current_user)
    db.commit()
    return {
        "id": apr.external_id,
        "status": "submitted",
        "submitted_at": apr.atualizado_em,
    }
