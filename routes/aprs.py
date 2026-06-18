from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete
import asyncio
from datetime import datetime
from uuid import uuid4
import json
import logging
import mimetypes
import os
from pathlib import Path
import shutil

from database import get_db
from models import APR, Passo, APREvent, APRShare, User, RiskItem, Company
import schemas
from apr_flow import get_activity_suggestions
from apr_documents import write_apr_pdf, validate_apr_for_pdf, PDF_TEMPLATE_VERSION
from excel_contract import get_excel_hashes
from ai_suggestions import (
    generate_ai_step_image,
    generate_ai_steps_from_image,
    AIConfigError,
    AIResponseError,
    AITextInvalidEncodingError,
)
from api_errors import ApiError, missing_fields_error
from text_normalizer import normalize_text, normalize_list
from auth import get_current_user
from request_guards import apply_rate_limit, request_identity
from plan_utils import get_plan_tier, normalize_plan_name
from risk_engine import (
    compute_risk_score,
    rebuild_risk_items_for_apr,
    list_risk_items_for_apr,
    has_invalid_risk_items,
)
from status_utils import normalize_status
from rbac import can_write, normalize_role
from norm_profile_service import apply_profile_snapshot_to_apr, resolve_norm_profile

router = APIRouter(prefix="/v1/aprs", tags=["APR"])
logger = logging.getLogger(__name__)
_EVIDENCE_DIR = Path("uploads") / "step_evidence"
_STATUS_RASCUNHO = "rascunho"
_STATUS_ENVIADO = "enviado"
_STATUS_APROVADO = "aprovado"
_STATUS_REPROVADO = "reprovado"
_STATUS_ARQUIVADO = "arquivado"
_EDITABLE_STATUSES = {_STATUS_RASCUNHO, _STATUS_REPROVADO, "draft", "rejected"}
_AI_KEY_ERROR_TOKENS = (
    "api key not found",
    "api key invalid",
    "api_key_invalid",
    "api_key_service_blocked",
)


class AIStepImage(BaseModel):
    step_order: int = Field(..., ge=1)
    description: str
    hazard: str
    consequences: str
    safeguards: str
    epis: list[str]
    regulations: list[str] = Field(default_factory=list)


class AIStepsImageResponse(BaseModel):
    steps: list[AIStepImage]


class APRStatusUpdateRequest(BaseModel):
    status: str
    reason: str | None = None


def _invalidate_dashboard_cache(company_id: int | None, event_dt: datetime | None = None) -> None:
    if not company_id:
        return
    try:
        from routes.risk_dashboard import get_redis_client, invalidate_risk_dashboard_cache

        redis = get_redis_client()
        if redis is None:
            return
        asyncio.run(
            invalidate_risk_dashboard_cache(
                redis=redis,
                company_id=int(company_id),
                event_dt=event_dt or datetime.utcnow(),
            )
        )
    except Exception:
        logger.debug("Falha ao invalidar cache do dashboard de riscos", exc_info=True)


def _public_ai_error_message(message: str) -> str:
    msg = (message or "").strip()
    lowered = msg.lower()
    if any(token in lowered for token in _AI_KEY_ERROR_TOKENS):
        return "Servico de IA indisponivel no momento. Tente novamente em instantes."
    if "nao configurada" in lowered and "gemini_api_key" in lowered:
        return "Servico de IA indisponivel no momento. Tente novamente em instantes."
    if "quota exceeded" in lowered or "rate limit" in lowered:
        return "Cota da IA esgotada no momento. Aguarde alguns minutos e tente novamente."
    return msg or "Falha ao gerar passos com IA"


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


def _normalize_scope_ref(value: str | None) -> str | None:
    normalized = normalize_text(value, keep_newlines=False, origin="user", field="scope_ref")
    if not normalized:
        return None
    return normalized


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
            message="APR precisa estar finalizada para esta aÃ§Ã£o",
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


def _stage_from_status(normalized_status: str) -> str:
    if normalized_status == "draft":
        return "criar"
    if normalized_status == "submitted":
        return "aprovacao"
    if normalized_status == "rejected":
        return "controles"
    if normalized_status in {"approved", "final"}:
        return "execucao"
    if normalized_status == "archived":
        return "relatorio"
    return "perigos"


def _apr_mutation_identity(request: Request, user: User, resource: str | None = None) -> str:
    principal = str(user.id)
    if resource:
        principal = f"{user.id}:{resource}"
    return request_identity(request, principal)


@router.post("", response_model=schemas.APROut)
def criar_apr(
    payload: schemas.APRCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_create", _apr_mutation_identity(request, current_user), limit=30, window_seconds=60)
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
        contract_id=_normalize_scope_ref(payload.contract_id),
        unit_id=_normalize_scope_ref(payload.unit_id),
        date=payload.date,
        activity_id=payload.activity_id,
        activity_name=payload.activity_name or payload.titulo or titulo,
        company_id=current_user.company_id,
        user_id=current_user.id,
        status="rascunho",
    )
    profile, resolved_from = resolve_norm_profile(
        db,
        company_id=int(current_user.company_id),
        contract_id=apr.contract_id,
        unit_id=apr.unit_id,
        actor_user_id=current_user.id,
    )
    apply_profile_snapshot_to_apr(apr, profile, resolved_from=resolved_from)
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
            "contract_id": apr.contract_id,
            "unit_id": apr.unit_id,
            "norm_profile_id": apr.norm_profile_id,
            "norm_profile_version": apr.norm_profile_version,
            "norm_profile_mode": apr.norm_profile_mode,
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
    has_steps_with_risks = any((passo.riscos or "").strip() for passo in apr.passos)
    has_risk_items = len(apr.risk_items) > 0
    suspicious_flat_matrix = False
    if has_risk_items:
        scores = [int(item.score or 0) for item in apr.risk_items]
        # "Tudo em PxS 1" costuma indicar matriz antiga/desatualizada sem inferencia real.
        suspicious_flat_matrix = bool(scores) and all(score <= 1 for score in scores)

    needs_rebuild = has_steps_with_risks and (
        not has_risk_items
        or has_invalid_risk_items(apr.risk_items)
        or suspicious_flat_matrix
    )
    if needs_rebuild:
        rebuild_risk_items_for_apr(db, apr_id)
        db.commit()
        db.refresh(apr)
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
    request: Request,
    file: UploadFile | None = File(default=None),
    descricao: str | None = Form(default=None),
    max_steps: int = Form(default=6),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_ai_steps", _apr_mutation_identity(request, current_user, str(apr_id)), limit=10, window_seconds=300)
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

    normative_context: dict[str, object] = {}
    if apr.company_id:
        profile, resolved_from = resolve_norm_profile(
            db,
            company_id=int(apr.company_id),
            contract_id=apr.contract_id,
            unit_id=apr.unit_id,
            actor_user_id=current_user.id,
        )
        apply_profile_snapshot_to_apr(apr, profile, resolved_from=resolved_from)
        normative_context = {
            "base_framework_id": profile.base_framework_id,
            "optional_framework_ids": profile.optional_framework_ids,
            "active_frameworks": [
                profile.base_framework_id,
                *profile.optional_framework_ids,
            ],
            "risk_engine_mode": profile.risk_engine_mode,
            "profile_version": profile.version,
        }

    activity_context: dict[str, object] = {}
    if apr.activity_id:
        try:
            suggestions = get_activity_suggestions(apr.activity_id)
            if suggestions:
                raw_steps = suggestions.get("steps") or []
                step_descriptions = [
                    str(step.get("description") or "").strip()
                    for step in raw_steps
                    if isinstance(step, dict) and str(step.get("description") or "").strip()
                ]
                agg = suggestions.get("suggestions") or {}
                activity = suggestions.get("activity") or {}
                activity_context = {
                    "activity_id": activity.get("id") or apr.activity_id,
                    "activity_name": activity.get("name") or apr.activity_name,
                    "step_descriptions": step_descriptions[:4],
                    "hazards": list(agg.get("hazards") or [])[:8],
                    "measures": list(agg.get("measures") or [])[:8],
                    "regulations": list(agg.get("regulations") or [])[:10],
                }
        except Exception:
            logger.debug(
                "Falha ao carregar contexto do Excel para IA na APR %s",
                apr_id,
                exc_info=True,
            )

    try:
        result = generate_ai_steps_from_image(
            image_bytes=image_bytes,
            image_mime=image_mime,
            descricao=descricao,
            max_steps=max_steps,
            activity_context=activity_context,
            normative_context=normative_context,
        )
    except AIConfigError as exc:
        raise ApiError(
            status_code=503,
            code="ai_not_configured",
            message=_public_ai_error_message(str(exc)),
            field=None,
        )
    except AITextInvalidEncodingError as exc:
        raise ApiError(
            status_code=502,
            code="AI_TEXT_INVALID_ENCODING",
            message=str(exc),
            field="ai_output",
        )
    except AIResponseError as exc:
        logger.warning("IA falhou para APR %s: %s", apr_id, exc)
        message = _public_ai_error_message(str(exc))
        if "alta demanda" in message:
            raise ApiError(status_code=429, code="ai_rate_limited", message=message, field=None)
        raise ApiError(status_code=502, code="ai_error", message=message, field=None)
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
        {
            "count": len(result.get("steps") or []),
            "has_image": bool(image_bytes),
            "norm_profile_mode": apr.norm_profile_mode,
            "norm_profile_version": apr.norm_profile_version,
            "has_excel_context": bool(activity_context),
        },
        actor=current_user,
    )
    db.commit()

    return result


@router.patch("/{apr_id}", response_model=schemas.APROut)
def atualizar_apr(
    apr_id: int,
    payload: schemas.APRUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_update", _apr_mutation_identity(request, current_user, str(apr_id)), limit=60, window_seconds=60)
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
        "contract_id",
        "unit_id",
        "date",
        "activity_id",
        "activity_name",
        "titulo",
        "risco",
        "descricao",
    ]:
        value = getattr(payload, field)
        if value is not None:
            if field in {"contract_id", "unit_id"}:
                value = _normalize_scope_ref(value)
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

    if apr.norm_profile_id is None or "contract_id" in updates or "unit_id" in updates:
        company_id_for_profile = apr.company_id or current_user.company_id
        if not company_id_for_profile:
            raise ApiError(status_code=403, code="forbidden", message="APR sem empresa vinculada", field="company_id")
        profile, resolved_from = resolve_norm_profile(
            db,
            company_id=int(company_id_for_profile),
            contract_id=apr.contract_id,
            unit_id=apr.unit_id,
            actor_user_id=current_user.id,
        )
        apply_profile_snapshot_to_apr(apr, profile, resolved_from=resolved_from)
        updates["norm_profile_id"] = profile.id
        updates["norm_profile_version"] = profile.version
        updates["norm_profile_mode"] = profile.risk_engine_mode

    if updates:
        _add_event(db, apr.id, "updated", updates, actor=current_user)
        db.commit()
        db.refresh(apr)
    return apr


@router.patch("/{apr_id}/status", response_model=schemas.APROut)
def atualizar_status_apr(
    apr_id: int,
    payload: APRStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_status_update", _apr_mutation_identity(request, current_user, str(apr_id)), limit=30, window_seconds=60)
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
    apr.current_stage = _stage_from_status(next_normalized)
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_delete", _apr_mutation_identity(request, current_user, str(apr_id)), limit=20, window_seconds=60)
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    current_normalized, _ = _normalize_status_label(apr.status or _STATUS_RASCUNHO)
    _validate_status_transition(current_normalized, "archived")
    apr.status = _STATUS_ARQUIVADO
    apr.current_stage = "relatorio"
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_step_create", _apr_mutation_identity(request, current_user, str(apr_id)), limit=60, window_seconds=60)
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
    _invalidate_dashboard_cache(apr.company_id)
    return passo


@router.patch("/{apr_id}/passos/{passo_id}", response_model=schemas.PassoOut)
def atualizar_passo(
    apr_id: int,
    passo_id: int,
    payload: schemas.PassoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_step_update", _apr_mutation_identity(request, current_user, f"{apr_id}:{passo_id}"), limit=60, window_seconds=60)
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
    _invalidate_dashboard_cache(apr.company_id if apr else passo.company_id)
    return passo


@router.delete("/{apr_id}/passos/{passo_id}")
def remover_passo(
    apr_id: int,
    passo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_step_delete", _apr_mutation_identity(request, current_user, f"{apr_id}:{passo_id}"), limit=30, window_seconds=60)
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
    _invalidate_dashboard_cache(apr.company_id if apr else passo.company_id)
    return {"status": "ok"}


@router.post("/{apr_id}/passos/{passo_id}/evidencia", response_model=schemas.TechnicalEvidenceOut)
def adicionar_evidencia(
    apr_id: int,
    passo_id: int,
    request: Request,
    file: UploadFile = File(...),
    caption: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_evidence_upload", _apr_mutation_identity(request, current_user, f"{apr_id}:{passo_id}"), limit=20, window_seconds=300)
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


@router.post("/{apr_id}/passos/{passo_id}/evidencia/ai", response_model=schemas.TechnicalEvidenceOut)
def adicionar_evidencia_ai(
    apr_id: int,
    passo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_evidence_ai", _apr_mutation_identity(request, current_user, f"{apr_id}:{passo_id}"), limit=10, window_seconds=300)
    _ensure_write_access(current_user)
    apr, passo = _get_passo_with_access(db, apr_id, passo_id, current_user)
    _ensure_editable(apr)

    activity = apr.activity_name or apr.titulo or "Atividade operacional"
    step_description = passo.descricao or ""
    hazards = passo.perigos or ""
    consequences = passo.riscos or ""
    safeguards = passo.medidas_controle or ""
    epis = passo.epis or ""
    regulations = passo.normas or ""

    try:
        image_result = generate_ai_step_image(
            activity=activity,
            step_description=step_description,
            hazards=hazards,
            consequences=consequences,
            safeguards=safeguards,
            epis=epis,
            regulations=regulations,
        )
    except AIConfigError as exc:
        raise ApiError(
            status_code=503,
            code="ai_not_configured",
            message=_public_ai_error_message(str(exc)),
            field=None,
        )
    except AIResponseError as exc:
        logger.warning("IA de imagem falhou para APR %s passo %s: %s", apr_id, passo_id, exc)
        message = _public_ai_error_message(str(exc))
        if "alta demanda" in message:
            raise ApiError(status_code=429, code="ai_rate_limited", message=message, field=None)
        raise ApiError(status_code=502, code="ai_error", message=message, field=None)
    except Exception:
        logger.exception("Erro inesperado ao gerar evidencia de imagem por IA")
        raise ApiError(
            status_code=500,
            code="ai_error",
            message="Falha ao gerar imagem por IA",
            field=None,
        )

    image_bytes = image_result.get("bytes")
    image_mime = str(image_result.get("mime") or "").lower()
    source = str(image_result.get("source") or "ai_provider")
    if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
        raise ApiError(
            status_code=502,
            code="ai_error",
            message="IA retornou imagem invalida",
            field=None,
        )

    ext = ".png" if "png" in image_mime else ".jpg"
    evidence_dir = _ensure_evidence_dir()
    new_filename = f"{uuid4().hex}{ext}"
    path = evidence_dir / new_filename

    with path.open("wb") as buffer:
        buffer.write(image_bytes)

    if passo.evidence_filename:
        old_path = evidence_dir / passo.evidence_filename
        try:
            if old_path.exists():
                old_path.unlink()
        except Exception:
            logger.warning("Falha ao remover evidencia antiga do passo %s", passo_id)

    passo.evidence_type = "image_ai"
    passo.evidence_filename = new_filename
    passo.evidence_caption = normalize_text(
        f"Imagem gerada por IA ({source}) para o passo {passo.ordem}",
        keep_newlines=False,
        origin="ai",
        field="caption",
    )
    passo.evidence_uploaded_at = datetime.utcnow()

    _add_event(
        db,
        apr_id,
        "evidence_ai_generated",
        {"passo_id": passo_id, "filename": new_filename, "source": source},
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_evidence_delete", _apr_mutation_identity(request, current_user, f"{apr_id}:{passo_id}"), limit=30, window_seconds=60)
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_steps_bulk", _apr_mutation_identity(request, current_user, str(apr_id)), limit=20, window_seconds=60)
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
    _invalidate_dashboard_cache(apr.company_id)

    db.refresh(apr)
    return apr


@router.post("/{apr_id}/apply-activity", response_model=schemas.APRDetail)
def aplicar_atividade(
    apr_id: int,
    payload: schemas.ActivityApply,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_apply_activity", _apr_mutation_identity(request, current_user, str(apr_id)), limit=20, window_seconds=60)
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
    _invalidate_dashboard_cache(apr.company_id)
    db.refresh(apr)
    return apr


@router.patch("/{apr_id}/risk-items/{risk_item_id}", response_model=schemas.RiskItemOut)
def atualizar_risk_item(
    apr_id: int,
    risk_item_id: int,
    payload: schemas.RiskItemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_risk_item_update", _apr_mutation_identity(request, current_user, f"{apr_id}:{risk_item_id}"), limit=60, window_seconds=60)
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
        _invalidate_dashboard_cache(apr.company_id)

    return risk_item


@router.post("/{apr_id}/finalize", response_model=schemas.APROut)
def finalizar_apr(
    apr_id: int,
    payload: schemas.APRFinalize,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_finalize", _apr_mutation_identity(request, current_user, str(apr_id)), limit=10, window_seconds=60)
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
            message="ConfirmaÃ§Ã£o do responsÃ¡vel tÃ©cnico nÃ£o confere com o cadastro atual",
            field="responsible_confirm",
        )

    passos = db.execute(select(Passo).where(Passo.apr_id == apr_id)).scalars().all()
    rebuild_risk_items_for_apr(db, apr_id)
    db.commit()
    _invalidate_dashboard_cache(apr.company_id)
    risk_items = list_risk_items_for_apr(db, apr_id)

    validate_apr_for_pdf(apr, passos, risk_items)

    apr.status = "final"
    apr.current_stage = "relatorio"
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
    _invalidate_dashboard_cache(apr.company_id)
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apply_rate_limit("aprs_share", _apr_mutation_identity(request, current_user, str(apr_id)), limit=10, window_seconds=300)
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    _ensure_finalized(apr)

    passos = db.execute(select(Passo).where(Passo.apr_id == apr_id)).scalars().all()
    rebuild_risk_items_for_apr(db, apr_id)
    db.commit()
    _invalidate_dashboard_cache(apr.company_id)
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



