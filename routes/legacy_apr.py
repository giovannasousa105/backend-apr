from datetime import date, datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import SessionLocal
from models import APR, Passo, APREvent, EPI, Perigo, User
import schemas
from apr_documents import write_apr_pdf, validate_apr_for_pdf, PDF_TEMPLATE_VERSION
from excel_contract import get_excel_hashes
from ai_suggestions import (
    generate_ai_steps,
    AIConfigError,
    AIResponseError,
    AITextInvalidEncodingError,
)
from api_errors import ApiError, missing_fields_error
from text_normalizer import normalize_text, normalize_list
from auth import get_current_user
from risk_engine import rebuild_risk_items_for_apr, list_risk_items_for_apr
from status_utils import is_final_status
from rbac import can_write, normalize_role


router = APIRouter(tags=["APR Legacy"])
logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _split_list(value, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in normalize_list(value, origin="user", field=field) if v]
    text = normalize_text(value, keep_newlines=False, origin="user", field=field) or ""
    if not text:
        return []
    parts = []
    for chunk in text.replace(",", ";").replace("/", ";").split(";"):
        item = normalize_text(chunk, keep_newlines=False, origin="user", field=field) or ""
        if item:
            parts.append(item)
    return parts


def _join_list(value, field: str) -> str:
    return "; ".join(_split_list(value, field))


def _add_event(db: Session, apr_id: int, event: str, payload: dict | None) -> None:
    _add_event_with_actor(db, apr_id, event, payload, actor=None)


def _add_event_with_actor(
    db: Session,
    apr_id: int,
    event: str,
    payload: dict | None,
    *,
    actor: User | None = None,
) -> None:
    data_payload = payload.copy() if payload else {}
    if actor:
        data_payload["actor"] = {
            "id": actor.id,
            "email": actor.email,
            "name": actor.name,
            "role": normalize_role(actor.role),
        }
    apr = db.get(APR, apr_id)
    company_id = apr.company_id if apr else None
    db.add(APREvent(apr_id=apr_id, company_id=company_id, event=event, payload=json_dumps(data_payload)))


def json_dumps(payload: dict | None) -> str | None:
    if not payload:
        return None
    import json
    return json.dumps(payload, ensure_ascii=False)


class APRCreateLegacy(BaseModel):
    obra: str | None = None
    local: str | None = None
    responsavel: str | None = None
    data: date | None = None
    atividade_id: str | None = None
    atividade_nome: str | None = None
    titulo: str | None = None
    risco: str | None = None
    descricao: str | None = None
    dangerous_energies_checklist: schemas.DangerousEnergiesChecklist | None = None


class APRItemCreate(BaseModel):
    descricao: str | None = None
    perigos: list[str] | str = []
    riscos: list[str] | str = []
    epis: list[str] | str = []
    medidas: list[str] | str = []
    normas: list[str] | str = []


class AIStep(BaseModel):
    passo: str
    perigo: str
    consequencia: str
    salvaguarda: str
    epi: str


class AIStepsRequest(BaseModel):
    atividade: str | None = None
    descricao: str | None = None
    ferramentas: list[str] = Field(default_factory=list)
    energias: list[str] = Field(default_factory=list)
    dangerous_energies_checklist: schemas.DangerousEnergiesChecklist | None = None
    max_steps: int = Field(default=6, ge=1, le=12)


class AIStepsResponse(BaseModel):
    passos: list[AIStep]
    source: str


class CatalogItem(BaseModel):
    id: int
    name: str


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


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


@router.post("/apr", response_model=schemas.APROut)
def criar_apr_legacy(
    payload: APRCreateLegacy,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    if not current_user.company_id:
        raise ApiError(status_code=403, code="forbidden", message="Usuario sem empresa vinculada", field="company_id")
    obra = normalize_text(payload.obra, keep_newlines=False, origin="user", field="obra")
    local = normalize_text(payload.local, keep_newlines=False, origin="user", field="local")
    responsavel = normalize_text(payload.responsavel, keep_newlines=False, origin="user", field="responsavel")
    atividade_id = normalize_text(payload.atividade_id, keep_newlines=False, origin="user", field="atividade_id")
    atividade_nome = normalize_text(payload.atividade_nome, keep_newlines=False, origin="user", field="atividade_nome")
    titulo = normalize_text(payload.titulo, keep_newlines=False, origin="user", field="titulo")
    risco = normalize_text(payload.risco, keep_newlines=False, origin="user", field="risco")
    descricao = normalize_text(payload.descricao, keep_newlines=True, origin="user", field="descricao")

    missing = []
    if _is_missing(obra):
        missing.append("obra")
    if _is_missing(local):
        missing.append("local")
    if _is_missing(responsavel):
        missing.append("responsavel")
    if not payload.data:
        missing.append("data")
    if _is_missing(atividade_id):
        missing.append("atividade_id")
    if _is_missing(atividade_nome):
        missing.append("atividade_nome")
    if _is_missing(titulo):
        missing.append("titulo")
    if _is_missing(risco):
        missing.append("risco")
    if _is_missing(descricao):
        missing.append("descricao")

    if missing:
        logger.warning("APR legacy invalida: campos obrigatorios faltando: %s", ", ".join(missing))
        raise missing_fields_error(missing)

    titulo = atividade_nome or titulo or "APR"
    risco = risco or "indefinido"

    worksite = local or obra
    sector = obra if local else None

    apr = APR(
        titulo=titulo,
        risco=risco,
        descricao=descricao,
        worksite=worksite,
        sector=sector,
        responsible=responsavel,
        date=payload.data,
        activity_id=atividade_id,
        activity_name=atividade_nome or titulo,
        company_id=current_user.company_id,
        user_id=current_user.id,
        status="rascunho",
    )
    if payload.dangerous_energies_checklist is not None:
        apr.dangerous_energies_checklist = payload.dangerous_energies_checklist
    apr.source_hashes = json_dumps(get_excel_hashes())
    db.add(apr)
    db.commit()
    db.refresh(apr)

    _add_event_with_actor(
        db,
        apr.id,
        "created_legacy",
        {
            "obra": apr.worksite,
            "local": apr.sector,
            "responsavel": apr.responsible,
            "data": apr.date.isoformat() if apr.date else None,
            "atividade_id": apr.activity_id,
            "atividade_nome": apr.activity_name,
        },
        actor=current_user,
    )
    db.commit()
    return apr


@router.get("/apr/{apr_id}", response_model=schemas.APRDetail)
def obter_apr_legacy(
    apr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    return apr


@router.post("/apr/{apr_id}/itens", response_model=schemas.PassoOut)
def adicionar_itens_legacy(
    apr_id: int,
    payload: APRItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)

    max_ordem = (
        db.execute(select(func.max(Passo.ordem)).where(Passo.apr_id == apr_id))
        .scalar_one()
        or 0
    )
    ordem = max_ordem + 1

    passo = Passo(
        apr_id=apr_id,
        company_id=apr.company_id,
        ordem=ordem,
        descricao=normalize_text(payload.descricao, keep_newlines=True, origin="user", field="descricao") or "",
        perigos=_join_list(payload.perigos, "perigos"),
        riscos=_join_list(payload.riscos, "riscos"),
        medidas_controle=_join_list(payload.medidas, "medidas"),
        epis=_join_list(payload.epis, "epis"),
        normas=_join_list(payload.normas, "normas"),
    )
    db.add(passo)
    db.commit()
    db.refresh(passo)
    rebuild_risk_items_for_apr(db, apr_id)

    _add_event_with_actor(
        db,
        apr_id,
        "item_added_legacy",
        {"ordem": ordem},
        actor=current_user,
    )
    db.commit()
    return passo


@router.post("/apr/{apr_id}/ia-sugestoes", response_model=AIStepsResponse)
def sugerir_passos_com_ia(
    apr_id: int,
    payload: AIStepsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_write_access(current_user)
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)

    atividade = payload.atividade or apr.activity_name or apr.titulo or ""
    descricao = payload.descricao or apr.descricao or ""
    contexto = {
        "Obra": apr.worksite,
        "Setor": apr.sector,
        "Responsavel": apr.responsible,
        "Data": apr.date.isoformat() if apr.date else None,
        "Risco": apr.risco,
    }

    try:
        result = generate_ai_steps(
            atividade=atividade,
            descricao=descricao,
            ferramentas=payload.ferramentas,
            energias=payload.energias,
            contexto=contexto,
            max_steps=payload.max_steps,
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

    _add_event_with_actor(
        db,
        apr_id,
        "ai_suggestions",
        {"count": len(result.get("passos") or []), "source": result.get("source")},
        actor=current_user,
    )
    db.commit()

    return result


@router.post("/apr/{apr_id}/gerar-pdf")
def gerar_pdf_legacy(
    apr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    apr = db.get(APR, apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")
    _ensure_apr_access(apr, current_user)
    if not is_final_status(apr.status):
        raise ApiError(
            status_code=400,
            code="apr_not_final",
            message="APR precisa estar finalizada para gerar PDF",
            field="status",
        )

    passos = db.execute(select(Passo).where(Passo.apr_id == apr_id)).scalars().all()
    rebuild_risk_items_for_apr(db, apr_id)
    db.commit()
    risk_items = list_risk_items_for_apr(db, apr_id)

    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"apr_{apr_id}_{stamp}.pdf"
    try:
        validate_apr_for_pdf(apr, passos, risk_items)
    except ApiError as exc:
        logger.warning("APR legacy %s nao pode gerar PDF: %s", apr_id, exc.message)
        raise

    try:
        path = write_apr_pdf(apr, passos, filename, risk_items)
    except Exception:
        logger.exception("Falha ao gerar PDF legacy da APR %s", apr_id)
        raise HTTPException(status_code=500, detail="Falha ao gerar PDF")

    if not apr.source_hashes:
        apr.source_hashes = json_dumps(get_excel_hashes())
    apr.template_version = PDF_TEMPLATE_VERSION

    _add_event_with_actor(
        db,
        apr_id,
        "pdf_generated_legacy",
        {"file": filename},
        actor=current_user,
    )
    db.commit()

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=filename,
    )


@router.get("/catalogo/epis", response_model=list[CatalogItem])
def listar_catalogo_epis(
    q: str | None = None,
    limit: int = 30,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    limit = min(max(limit, 1), 200)
    stmt = select(EPI)
    if q:
        stmt = stmt.where(EPI.epi.ilike(f"%{q}%"))
    items = db.execute(stmt.limit(limit)).scalars().all()
    return [
        {
            "id": item.id,
            "name": normalize_text(item.epi, keep_newlines=False, origin="excel", field="epi") or "",
        }
        for item in items
    ]


@router.get("/catalogo/perigos", response_model=list[CatalogItem])
def listar_catalogo_perigos(
    q: str | None = None,
    limit: int = 30,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    limit = min(max(limit, 1), 200)
    stmt = select(Perigo)
    if q:
        stmt = stmt.where(Perigo.perigo.ilike(f"%{q}%"))
    items = db.execute(stmt.limit(limit)).scalars().all()
    return [
        {
            "id": item.id,
            "name": normalize_text(item.perigo, keep_newlines=False, origin="excel", field="perigo") or "",
        }
        for item in items
    ]
