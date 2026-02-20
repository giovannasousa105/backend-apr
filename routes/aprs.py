from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete
from datetime import datetime
from uuid import uuid4
import json
import logging
import mimetypes
import os
from pathlib import Path
import shutil

from database import SessionLocal
from models import APR, Passo, APREvent, APRShare, User, RiskItem, Company
import schemas
from apr_flow import get_activity_suggestions
from apr_documents import write_apr_pdf, validate_apr_for_pdf, PDF_TEMPLATE_VERSION
from excel_contract import get_excel_hashes
from ai_suggestions import (
    generate_ai_steps_from_image,
    AIConfigError,
    AIResponseError,
    AITextInvalidEncodingError,
)
from api_errors import ApiError, missing_fields_error
from text_normalizer import normalize_text, normalize_list
from auth import get_current_user
from plan_utils import get_plan_tier, normalize_plan_name
from risk_engine import compute_risk_score, rebuild_risk_items_for_apr, list_risk_items_for_apr
from status_utils import normalize_status
from rbac import can_write, normalize_role

router = APIRouter(prefix="/v1/aprs", tags=["APR"])
logger = logging.getLogger(__name__)
_EVIDENCE_DIR = Path("uploads") / "step_evidence"
_STATUS_RASCUNHO = "rascunho"
_STATUS_ENVIADO = "enviado"
_STATUS_APROVADO = "aprovado"
_STATUS_REPROVADO = "reprovado"
_STATUS_ARQUIVADO = "arquivado"
_EDITABLE_STATUSES = {_STATUS_RASCUNHO, _STATUS_REPROVADO, "draft", "rejected"}


class AIStepImage(BaseModel):
    step_order: int = Field(..., ge=1)
    description: str
    hazard: str
    consequences: str
    safeguards: str
    epis: list[str]


class AIStepsImageResponse(BaseModel):
    steps: list[AIStepImage]


class APRStatusUpdateRequest(BaseModel):
    status: str
    reason: str | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _join_list(value, *, origin: str, field: str) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join([v for v in normalize_list(value, origin=origin, field=field) if v])
    return normalize_text(value, keep_newlines=False, origin=origin, field=field) or ""


def _actor_payload(user: User | None) -> dict | None:
    if not user:
        return None
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": normalize_role(user.role),
    }


def _add_event(
    db: Session,
    apr_id: int,
    event: str,
    payload: dict | None,
    *,
    actor: User | None = None,
) -> None:
    data_payload = payload.copy() if payload else {}
    actor_data = _actor_payload(actor)
    if actor_data:
        data_payload["actor"] = actor_data
    data = json.dumps(data_payload, ensure_ascii=False) if data_payload else None
    apr = db.get(APR, apr_id)
    company_id = apr.company_id if apr else None
    db.add(APREvent(apr_id=apr_id, company_id=company_id, event=event, payload=data))


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _validate_required_apr_fields(payload: schemas.APRCreate) -> None:
    missing = []
    if _is_missing(payload.sector):
        missing.append("obra")
    if _is_missing(payload.worksite):
        missing.append("local")
    if _is_missing(payload.responsible):
        missing.append("responsavel")
    if not payload.date:
        missing.append("data")
    if _is_missing(payload.activity_id):
        missing.append("atividade_id")
    if _is_missing(payload.activity_name):
        missing.append("atividade_nome")
    if _is_missing(payload.titulo):
        missing.append("titulo")
    if _is_missing(payload.risco):
        missing.append("risco")
    if _is_missing(payload.descricao):
        missing.append("descricao")
    if missing:
        raise missing_fields_error(missing)


def _scope_apr_query(stmt, user: User):
    if not user.company_id:
        return stmt.where(APR.id == -1)
    return stmt.where(APR.company_id == user.company_id)


def _ensure_apr_access(apr: APR, user: User) -> None:
    if not user.company_id or not apr.company_id or apr.company_id != user.company_id:
        raise ApiError(status_code=403, code="forbidden", message="Acesso negado", field="apr_id")


def _ensure_write_access(user: User) -> None:
    if not can_write(normalize_role(user.role)):
        raise ApiError(
            status_code=403,
            code="forbidden",
            message="Perfil sem permissao de escrita",
            field="role",
        )


def _ensure_editable(apr: APR) -> None:
    status = normalize_status(apr.status)
    if status not in _EDITABLE_STATUSES:
        raise ApiError(
            status_code=400,
            code="apr_not_editable",
            message="APR no estado atual nao pode ser modificada",
            field="status",
        )


def _ensure_finalized(apr: APR) -> None:
    if normalize_status(apr.status) != "final":
        raise ApiError(
            status_code=400,
            code="apr_not_final",
            message="APR precisa estar finalizada para esta ação",
            field="status",
        )


def _get_passo_with_access(db: Session, apr_id: int, passo_id: int, user: User) -> tuple[APR, Passo]:
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, user)
    passo = db.get(Passo, passo_id)
    if not passo or passo.apr_id != apr_id:
        raise ApiError(status_code=404, code="not_found", message="Passo nao encontrado", field="passo_id")
    return apr, passo


def _ensure_evidence_dir() -> Path:
    _EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    return _EVIDENCE_DIR


_ARCHIVED_STATUSES = {"arquivado", "archived"}


def _count_active_aprs(db: Session, company_id: int | None) -> int:
    if not company_id:
        return 0
    stmt = (
        select(func.count())
        .select_from(APR)
        .where(
            APR.company_id == company_id,
            func.lower(APR.status).notin_(tuple(_ARCHIVED_STATUSES)),
        )
    )
    return db.execute(stmt).scalar_one()


def _normalize_status_label(value: str) -> tuple[str, str]:
    normalized = normalize_status(value)
    if normalized == "draft":
        return normalized, _STATUS_RASCUNHO
    if normalized == "submitted":
        return normalized, _STATUS_ENVIADO
    if normalized == "approved":
        return normalized, _STATUS_APROVADO
    if normalized == "rejected":
        return normalized, _STATUS_REPROVADO
    if normalized == "archived":
        return normalized, _STATUS_ARQUIVADO
    if normalized == "final":
        return normalized, "final"
    raise ApiError(status_code=400, code="validation_error", message="Status invalido", field="status")


def _validate_status_transition(current_status: str, next_status: str) -> None:
    allowed = {
        "draft": {"submitted", "archived"},
        "submitted": {"approved", "rejected", "archived"},
        "rejected": {"draft", "archived"},
        "approved": {"archived"},
        "final": {"archived"},
        "archived": set(),
    }
    if next_status not in allowed.get(current_status, set()):
        raise ApiError(
            status_code=400,
            code="invalid_status_transition",
            message=f"Transicao invalida de {current_status} para {next_status}",
            field="status",
        )


@router.post("", response_model=schemas.APROut)
def criar_apr(
    payload: schemas.APRCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    _validate_required_apr_fields(payload)
    if not current_user.company_id:
        raise ApiError(status_code=403, code="forbidden", message="Usuario sem empresa vinculada", field="company_id")
    company = db.get(Company, current_user.company_id) if current_user.company_id else None
    plan_name = normalize_plan_name(company.plan_name if company else None)
    plan_tier = get_plan_tier(plan_name)
    max_active_aprs = plan_tier.limits.max_active_aprs
    company_id_for_limit = company.id if company else current_user.company_id
    if max_active_aprs is not None and company_id_for_limit:
        active_count = _count_active_aprs(db, company_id_for_limit)
        if active_count >= max_active_aprs:
            raise ApiError(
                status_code=403,
                code="plan_limit_reached",
                message=f"Plano {plan_name.capitalize()} permite no maximo {max_active_aprs} APRs ativas. Atualize para o Plano Pro para criar novas APRs.",
                field="plan",
            )
    titulo = payload.activity_name or payload.titulo or "APR"
    risco = payload.risco or "indefinido"
    apr = APR(
        titulo=titulo,
        risco=risco,
        descricao=payload.descricao,
        worksite=payload.worksite,
        sector=payload.sector,
        responsible=payload.responsible,
        date=payload.date,
        activity_id=payload.activity_id,
        activity_name=payload.activity_name or payload.titulo or titulo,
        company_id=current_user.company_id,
        user_id=current_user.id,
        status="rascunho",
    )
    if payload.dangerous_energies_checklist is not None:
        apr.dangerous_energies_checklist = payload.dangerous_energies_checklist
    db.add(apr)
    db.commit()
    db.refresh(apr)
    _add_event(
        db,
        apr.id,
        "created",
        {
            "worksite": apr.worksite,
            "sector": apr.sector,
            "responsible": apr.responsible,
            "date": apr.date.isoformat() if apr.date else None,
            "activity_id": apr.activity_id,
            "activity_name": apr.activity_name,
        },
        actor=current_user,
    )
    db.commit()
    return apr


@router.get("", response_model=schemas.PaginatedOut[schemas.APROut])
def listar_aprs(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    limit = min(max(limit, 1), 200)
    base = _scope_apr_query(select(APR), current_user)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    items = db.execute(base.offset(skip).limit(limit)).scalars().all()
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{apr_id}", response_model=schemas.APRDetail)
def obter_apr(
    apr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    return apr


@router.get("/{apr_id}/suggestions", response_model=schemas.ActivitySuggestions)
def sugerir_para_apr(
    apr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    if not apr.activity_id:
        raise ApiError(status_code=400, code="missing_field", message="APR sem activity_id", field="activity_id")

    try:
        data = get_activity_suggestions(apr.activity_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not data:
        raise HTTPException(status_code=404, detail="Atividade nao encontrada")
    return data


@router.post("/{apr_id}/ai-steps", response_model=AIStepsImageResponse)
def gerar_passos_por_imagem(
    apr_id: int,
    file: UploadFile | None = File(default=None),
    descricao: str | None = Form(default=None),
    max_steps: int = Form(default=6),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)

    descricao = normalize_text(descricao, keep_newlines=True, origin="user", field="descricao")

    image_bytes: bytes | None = None
    image_mime: str | None = None
    if file is not None:
        content_type = file.content_type or ""
        filename = os.path.basename(file.filename or "")
        ext = os.path.splitext(filename)[1].lower()
        allowed_ext = {".png", ".jpg", ".jpeg", ".webp"}
        if not content_type.startswith("image/") and ext not in allowed_ext:
            raise ApiError(
                status_code=400,
                code="invalid_file",
                message="Arquivo deve ser uma imagem",
                field="file",
            )
        try:
            image_bytes = file.file.read()
        finally:
            try:
                file.file.close()
            except Exception:
                pass

        if not image_bytes:
            raise ApiError(
                status_code=400,
                code="invalid_file",
                message="Arquivo de imagem vazio",
                field="file",
            )

        if content_type.startswith("image/"):
            image_mime = content_type
        else:
            guessed = mimetypes.guess_type(filename)[0]
            image_mime = guessed or "image/jpeg"

    if image_bytes is None and _is_missing(descricao):
        raise ApiError(
            status_code=400,
            code="missing_field",
            message="Informe uma imagem ou descricao",
            field="descricao",
        )

    if max_steps < 1 or max_steps > 12:
        raise ApiError(
            status_code=400,
            code="validation_error",
            message="max_steps deve ser entre 1 e 12",
            field="max_steps",
        )

    try:
        result = generate_ai_steps_from_image(
            image_bytes=image_bytes,
            image_mime=image_mime,
            descricao=descricao,
            max_steps=max_steps,
        )
    except AIConfigError as exc:
        raise ApiError(status_code=503, code="ai_not_configured", message=str(exc), field=None)
    except AITextInvalidEncodingError as exc:
        raise ApiError(
            status_code=502,
            code="AI_TEXT_INVALID_ENCODING",
            message=str(exc),
            field="ai_output",
        )
    except AIResponseError as exc:
        logger.warning("IA falhou para APR %s: %s", apr_id, exc)
        raise ApiError(status_code=502, code="ai_error", message=str(exc), field=None)
    except Exception:
        logger.exception("Erro inesperado ao gerar passos com IA")
        raise ApiError(
            status_code=500,
            code="ai_error",
            message="Falha ao gerar passos com IA",
            field=None,
        )

    _add_event(
        db,
        apr_id,
        "ai_steps_image",
        {"count": len(result.get("steps") or []), "has_image": bool(image_bytes)},
        actor=current_user,
    )
    db.commit()

    return result


@router.patch("/{apr_id}", response_model=schemas.APROut)
def atualizar_apr(
    apr_id: int,
    payload: schemas.APRUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    _ensure_editable(apr)

    updates: dict[str, object] = {}
    for field in [
        "worksite",
        "sector",
        "responsible",
        "date",
        "activity_id",
        "activity_name",
        "titulo",
        "risco",
        "descricao",
    ]:
        value = getattr(payload, field)
        if value is not None:
            setattr(apr, field, value)
            updates[field] = value

    if payload.dangerous_energies_checklist is not None:
        apr.dangerous_energies_checklist = payload.dangerous_energies_checklist
        updates["dangerous_energies_checklist"] = True

    if "activity_name" in updates and "titulo" not in updates:
        apr.titulo = str(payload.activity_name)
        updates["titulo"] = apr.titulo
    if "titulo" in updates and "activity_name" not in updates:
        apr.activity_name = str(payload.titulo)
        updates["activity_name"] = apr.activity_name

    if updates:
        _add_event(db, apr.id, "updated", updates, actor=current_user)
        db.commit()
        db.refresh(apr)
    return apr


@router.patch("/{apr_id}/status", response_model=schemas.APROut)
def atualizar_status_apr(
    apr_id: int,
    payload: APRStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)

    current_normalized, _ = _normalize_status_label(apr.status or _STATUS_RASCUNHO)
    next_normalized, next_label = _normalize_status_label(payload.status)

    if current_normalized == next_normalized and apr.status == next_label:
        return apr

    _validate_status_transition(current_normalized, next_normalized)
    apr.status = next_label
    db.commit()
    db.refresh(apr)
    _add_event(
        db,
        apr.id,
        "status_changed",
        {
            "from": current_normalized,
            "to": next_normalized,
            "reason": payload.reason,
        },
        actor=current_user,
    )
    db.commit()
    return apr


@router.delete("/{apr_id}", response_model=dict)
def excluir_apr(
    apr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    current_normalized, _ = _normalize_status_label(apr.status or _STATUS_RASCUNHO)
    _validate_status_transition(current_normalized, "archived")
    apr.status = _STATUS_ARQUIVADO
    db.commit()
    _add_event(
        db,
        apr.id,
        "deleted",
        {"mode": "soft_delete", "status": "archived"},
        actor=current_user,
    )
    db.commit()
    return {"status": "ok", "apr_id": apr.id, "archived": True}


@router.post("/{apr_id}/passos", response_model=schemas.PassoOut)
def adicionar_passo(
    apr_id: int,
    payload: schemas.PassoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    _ensure_editable(apr)

    existe = db.execute(
        select(Passo).where(Passo.apr_id == apr_id, Passo.ordem == payload.ordem)
    ).scalar_one_or_none()
    if existe:
        raise ApiError(
            status_code=409,
            code="conflict",
            message="Ja existe um passo com essa ordem nesta APR",
            field="ordem",
        )

    passo = Passo(
        apr_id=apr_id,
        company_id=apr.company_id,
        ordem=payload.ordem,
        descricao=payload.descricao,
        perigos=payload.perigos,
        riscos=payload.riscos,
        medidas_controle=payload.medidas_controle,
        epis=payload.epis,
        normas=payload.normas,
    )
    db.add(passo)
    db.commit()
    db.refresh(passo)
    rebuild_risk_items_for_apr(db, apr_id)
    _add_event(
        db,
        apr_id,
        "step_added",
        {"ordem": passo.ordem, "descricao": passo.descricao},
        actor=current_user,
    )
    db.commit()
    return passo


@router.patch("/{apr_id}/passos/{passo_id}", response_model=schemas.PassoOut)
def atualizar_passo(
    apr_id: int,
    passo_id: int,
    payload: schemas.PassoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    passo = db.get(Passo, passo_id)
    if not passo or passo.apr_id != apr_id:
        raise ApiError(status_code=404, code="not_found", message="Passo nao encontrado", field="passo_id")
    apr = db.get(APR, apr_id)
    if apr:
        _ensure_apr_access(apr, current_user)
        _ensure_editable(apr)

    if payload.ordem is not None:
        existe = db.execute(
            select(Passo).where(
                Passo.apr_id == apr_id,
                Passo.ordem == payload.ordem,
                Passo.id != passo_id,
            )
        ).scalar_one_or_none()
        if existe:
            raise ApiError(
                status_code=409,
                code="conflict",
                message="Ja existe um passo com essa ordem nesta APR",
                field="ordem",
            )
        passo.ordem = payload.ordem

    if payload.descricao is not None:
        passo.descricao = payload.descricao
    if payload.perigos is not None:
        passo.perigos = payload.perigos
    if payload.riscos is not None:
        passo.riscos = payload.riscos
    if payload.medidas_controle is not None:
        passo.medidas_controle = payload.medidas_controle
    if payload.epis is not None:
        passo.epis = payload.epis
    if payload.normas is not None:
        passo.normas = payload.normas

    db.commit()
    db.refresh(passo)
    rebuild_risk_items_for_apr(db, apr_id)
    _add_event(db, apr_id, "step_updated", {"passo_id": passo_id}, actor=current_user)
    db.commit()
    return passo


@router.delete("/{apr_id}/passos/{passo_id}")
def remover_passo(
    apr_id: int,
    passo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    passo = db.get(Passo, passo_id)
    if not passo or passo.apr_id != apr_id:
        raise ApiError(status_code=404, code="not_found", message="Passo nao encontrado", field="passo_id")
    apr = db.get(APR, apr_id)
    if apr:
        _ensure_apr_access(apr, current_user)
        _ensure_editable(apr)
    db.delete(passo)
    db.commit()
    rebuild_risk_items_for_apr(db, apr_id)
    _add_event(db, apr_id, "step_removed", {"passo_id": passo_id}, actor=current_user)
    db.commit()
    return {"status": "ok"}


@router.post("/{apr_id}/passos/{passo_id}/evidencia", response_model=schemas.TechnicalEvidenceOut)
def adicionar_evidencia(
    apr_id: int,
    passo_id: int,
    file: UploadFile = File(...),
    caption: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr, passo = _get_passo_with_access(db, apr_id, passo_id, current_user)
    _ensure_editable(apr)

    content_type = file.content_type or ""
    filename = os.path.basename(file.filename or "")
    ext = os.path.splitext(filename)[1].lower()
    if not ext and content_type:
        guessed = mimetypes.guess_extension(content_type)
        if guessed:
            ext = guessed

    allowed_ext = {".png", ".jpg", ".jpeg", ".webp"}
    if not content_type.startswith("image/") and ext not in allowed_ext:
        raise ApiError(
            status_code=400,
            code="invalid_file",
            message="Arquivo deve ser uma imagem",
            field="file",
        )

    ext = ext if ext in allowed_ext else ".jpg"

    evidence_dir = _ensure_evidence_dir()
    new_filename = f"{uuid4().hex}{ext}"
    path = evidence_dir / new_filename

    try:
        with path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    if passo.evidence_filename:
        old_path = evidence_dir / passo.evidence_filename
        try:
            if old_path.exists():
                old_path.unlink()
        except Exception:
            logger.warning("Falha ao remover evidencia antiga do passo %s", passo_id)

    passo.evidence_type = "image"
    passo.evidence_filename = new_filename
    passo.evidence_caption = normalize_text(caption, keep_newlines=True, origin="user", field="caption")
    passo.evidence_uploaded_at = datetime.utcnow()

    _add_event(
        db,
        apr_id,
        "evidence_uploaded",
        {"passo_id": passo_id, "filename": new_filename},
        actor=current_user,
    )
    db.commit()
    db.refresh(passo)
    return passo.technical_evidence


@router.get("/{apr_id}/passos/{passo_id}/evidencia")
def baixar_evidencia(
    apr_id: int,
    passo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _apr, passo = _get_passo_with_access(db, apr_id, passo_id, current_user)
    if not passo.evidence_filename:
        raise ApiError(status_code=404, code="not_found", message="Evidencia nao encontrada", field="evidence")

    path = _EVIDENCE_DIR / passo.evidence_filename
    if not path.exists():
        raise ApiError(status_code=404, code="not_found", message="Arquivo nao encontrado", field="evidence")

    media_type, _ = mimetypes.guess_type(str(path))
    return FileResponse(path, media_type=media_type or "application/octet-stream")


@router.delete("/{apr_id}/passos/{passo_id}/evidencia")
def remover_evidencia(
    apr_id: int,
    passo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    _apr, passo = _get_passo_with_access(db, apr_id, passo_id, current_user)
    _ensure_editable(_apr)
    if not passo.evidence_filename:
        return {"status": "ok"}

    path = _EVIDENCE_DIR / passo.evidence_filename
    try:
        if path.exists():
            path.unlink()
    except Exception:
        logger.warning("Falha ao remover arquivo de evidencia do passo %s", passo_id)

    passo.evidence_type = None
    passo.evidence_filename = None
    passo.evidence_caption = None
    passo.evidence_uploaded_at = None

    _add_event(db, apr_id, "evidence_deleted", {"passo_id": passo_id}, actor=current_user)
    db.commit()
    return {"status": "ok"}


@router.post("/{apr_id}/steps/bulk", response_model=schemas.APRDetail)
def adicionar_passos_em_lote(
    apr_id: int,
    payload: schemas.PassoBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    _ensure_editable(apr)

    if payload.replace:
        db.execute(delete(Passo).where(Passo.apr_id == apr_id))

    existentes = {
        passo.ordem
        for passo in db.execute(select(Passo).where(Passo.apr_id == apr_id)).scalars().all()
    }
    novos = set()

    for item in payload.items:
        ordem = item.step_order
        if ordem in existentes or ordem in novos:
            raise ApiError(
                status_code=409,
                code="conflict",
                message=f"Ordem duplicada: {ordem}",
                field="step_order",
            )
        novos.add(ordem)

        passo = Passo(
            apr_id=apr_id,
            company_id=apr.company_id,
            ordem=ordem,
            descricao=item.description,
            perigos=_join_list(item.hazards, origin="user", field="hazards"),
            riscos=_join_list(item.risks, origin="user", field="risks"),
            medidas_controle=_join_list(item.measures, origin="user", field="measures"),
            epis=_join_list(item.epis, origin="user", field="epis"),
            normas=_join_list(item.regulations, origin="user", field="regulations"),
        )
        db.add(passo)

    db.commit()
    rebuild_risk_items_for_apr(db, apr_id)
    _add_event(
        db,
        apr_id,
        "steps_bulk_added",
        {"count": len(payload.items), "replace": payload.replace},
        actor=current_user,
    )
    db.commit()

    db.refresh(apr)
    return apr


@router.post("/{apr_id}/apply-activity", response_model=schemas.APRDetail)
def aplicar_atividade(
    apr_id: int,
    payload: schemas.ActivityApply,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    _ensure_editable(apr)

    activity_id = payload.activity_id or apr.activity_id
    if not activity_id:
        raise ApiError(
            status_code=400,
            code="missing_field",
            message="activity_id nao informado",
            field="activity_id",
        )

    try:
        data = get_activity_suggestions(activity_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not data:
        raise ApiError(
            status_code=404,
            code="not_found",
            message="Atividade nao encontrada",
            field="activity_id",
        )

    if payload.replace:
        db.execute(delete(Passo).where(Passo.apr_id == apr_id))

    steps = data.get("steps", [])
    for step in steps:
        passo = Passo(
            apr_id=apr_id,
            company_id=apr.company_id,
            ordem=step.get("step_order") or 0,
            descricao=step.get("description") or "",
            perigos=_join_list(step.get("hazards"), origin="excel", field="hazards"),
            riscos=_join_list(step.get("risks"), origin="excel", field="risks"),
            medidas_controle=_join_list(step.get("measures"), origin="excel", field="measures"),
            epis=_join_list(step.get("epis"), origin="excel", field="epis"),
            normas=_join_list(step.get("regulations"), origin="excel", field="regulations"),
        )
        db.add(passo)

    apr.activity_id = activity_id
    apr.activity_name = data["activity"].get("name")
    apr.titulo = apr.activity_name or apr.titulo
    if not apr.source_hashes:
        apr.source_hashes = json.dumps(get_excel_hashes(), ensure_ascii=False)

    db.commit()
    rebuild_risk_items_for_apr(db, apr_id)
    _add_event(
        db,
        apr_id,
        "activity_applied",
        {"activity_id": activity_id, "steps": len(steps), "replace": payload.replace},
        actor=current_user,
    )
    db.commit()
    db.refresh(apr)
    return apr


@router.patch("/{apr_id}/risk-items/{risk_item_id}", response_model=schemas.RiskItemOut)
def atualizar_risk_item(
    apr_id: int,
    risk_item_id: int,
    payload: schemas.RiskItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    _ensure_editable(apr)

    risk_item = db.get(RiskItem, risk_item_id)
    if not risk_item or risk_item.apr_id != apr_id:
        raise ApiError(
            status_code=404,
            code="not_found",
            message="Item de risco nao encontrado",
            field="risk_item_id",
        )

    updated = False
    if payload.probability is not None:
        risk_item.probability = int(payload.probability)
        updated = True
    if payload.severity is not None:
        risk_item.severity = int(payload.severity)
        updated = True

    if updated:
        score, level = compute_risk_score(risk_item.probability, risk_item.severity)
        if level == "invalid":
            raise ApiError(
                status_code=400,
                code="risk_score_invalid",
                message="Probabilidade e severidade devem estar entre 1 e 5 para gerar score valido",
                field="risk_items",
            )
        risk_item.score = score
        risk_item.risk_level = level
        db.commit()
        db.refresh(risk_item)

    return risk_item


@router.post("/{apr_id}/finalize", response_model=schemas.APROut)
def finalizar_apr(
    apr_id: int,
    payload: schemas.APRFinalize,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    _ensure_editable(apr)

    normalized_responsible = normalize_text(
        payload.responsible_confirm, keep_newlines=False, origin="user", field="responsible_confirm"
    )
    current_responsible = normalize_text(
        apr.responsible, keep_newlines=False, origin="system", field="responsible"
    )
    if not normalized_responsible or normalized_responsible != current_responsible:
        raise ApiError(
            status_code=400,
            code="responsible_mismatch",
            message="Confirmação do responsável técnico não confere com o cadastro atual",
            field="responsible_confirm",
        )

    passos = db.execute(select(Passo).where(Passo.apr_id == apr_id)).scalars().all()
    rebuild_risk_items_for_apr(db, apr_id)
    db.commit()
    risk_items = list_risk_items_for_apr(db, apr_id)

    validate_apr_for_pdf(apr, passos, risk_items)

    apr.status = "final"
    apr.template_version = PDF_TEMPLATE_VERSION
    _add_event(
        db,
        apr_id,
        "finalized",
        {
            "responsible_confirm": normalized_responsible,
            "position": payload.position,
            "crea": payload.crea,
        },
        actor=current_user,
    )
    db.commit()
    db.refresh(apr)
    return apr


@router.get("/{apr_id}/history", response_model=list[schemas.APREventOut])
def listar_historico(
    apr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    eventos = (
        db.execute(select(APREvent).where(APREvent.apr_id == apr_id).order_by(APREvent.criado_em))
        .scalars()
        .all()
    )

    saida = []
    for ev in eventos:
        payload = None
        if ev.payload:
            try:
                payload = json.loads(ev.payload)
            except Exception:
                payload = {"raw": ev.payload}
        saida.append(
            {
                "id": ev.id,
                "apr_id": ev.apr_id,
                "event": ev.event,
                "payload": payload,
                "criado_em": ev.criado_em,
            }
        )
    return saida


@router.get("/{apr_id}/pdf")
def gerar_pdf(
    apr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    _ensure_finalized(apr)

    passos = db.execute(select(Passo).where(Passo.apr_id == apr_id)).scalars().all()
    rebuild_risk_items_for_apr(db, apr_id)
    db.commit()
    risk_items = list_risk_items_for_apr(db, apr_id)

    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"apr_{apr_id}_{stamp}.pdf"
    try:
        validate_apr_for_pdf(apr, passos, risk_items)
    except ApiError as exc:
        logger.warning("APR %s nao pode gerar PDF: %s", apr_id, exc.message)
        raise

    try:
        path = write_apr_pdf(apr, passos, filename, risk_items)
    except Exception:
        logger.exception("Falha ao gerar PDF da APR %s", apr_id)
        raise HTTPException(status_code=500, detail="Falha ao gerar PDF")

    if not apr.source_hashes:
        apr.source_hashes = json.dumps(get_excel_hashes(), ensure_ascii=False)
    apr.template_version = PDF_TEMPLATE_VERSION

    _add_event(db, apr_id, "pdf_generated", {"file": filename}, actor=current_user)
    db.commit()

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=filename,
    )


@router.post("/{apr_id}/share", response_model=schemas.APRShareOut)
def criar_compartilhamento(
    apr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    _ensure_finalized(apr)

    passos = db.execute(select(Passo).where(Passo.apr_id == apr_id)).scalars().all()
    rebuild_risk_items_for_apr(db, apr_id)
    db.commit()
    risk_items = list_risk_items_for_apr(db, apr_id)

    token = uuid4().hex
    filename = f"apr_{apr_id}_{token}.pdf"
    try:
        validate_apr_for_pdf(apr, passos, risk_items)
    except ApiError as exc:
        logger.warning("APR %s nao pode gerar share PDF: %s", apr_id, exc.message)
        raise

    try:
        path = write_apr_pdf(apr, passos, filename, risk_items)
    except Exception:
        logger.exception("Falha ao gerar PDF compartilhado da APR %s", apr_id)
        raise HTTPException(status_code=500, detail="Falha ao gerar PDF")

    if not apr.source_hashes:
        apr.source_hashes = json.dumps(get_excel_hashes(), ensure_ascii=False)
    apr.template_version = PDF_TEMPLATE_VERSION

    share = APRShare(apr_id=apr_id, company_id=apr.company_id, token=token, filename=filename)
    db.add(share)
    db.commit()
    db.refresh(share)

    _add_event(
        db,
        apr_id,
        "share_created",
        {"token": token, "file": filename},
        actor=current_user,
    )
    db.commit()

    return {
        "apr_id": apr_id,
        "token": token,
        "share_url": f"/share/{token}",
        "filename": filename,
        "created_at": share.criado_em,
    }
