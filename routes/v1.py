from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select, func

from database import SessionLocal
from models import EPI, Perigo
from excel_contract import get_contract_cached, RISK_MATRIX
from api_errors import validation_error
import schemas
from auth import get_current_user, require_admin

router = APIRouter(prefix="/v1", tags=["v1"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/health")
def health():
    return {"status": "ok"}


# -------- CONTRATO EXCEL --------
@router.get("/contract")
@router.get("/schema")
def obter_contrato_excel(request: Request, _user=Depends(get_current_user)):
    contract, headers, not_modified = get_contract_cached(request.headers)
    if not_modified:
        return Response(status_code=304, headers=headers)
    return JSONResponse(content=contract, headers=headers)


# -------- LISTAGEM (com paginação + search) --------
@router.get("/epis", response_model=schemas.PaginatedEPIOut)
def listar_epis(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    limit = min(max(limit, 1), 200)

    base = select(EPI)
    if search:
        base = base.where(EPI.epi.ilike(f"%{search}%"))

    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    items = db.execute(base.offset(skip).limit(limit)).scalars().all()

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/perigos", response_model=schemas.PaginatedPerigoOut)
def listar_perigos(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    limit = min(max(limit, 1), 200)

    base = select(Perigo)
    if search:
        base = base.where(Perigo.perigo.ilike(f"%{search}%"))

    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    items = db.execute(base.offset(skip).limit(limit)).scalars().all()

    return {"items": items, "total": total, "skip": skip, "limit": limit}


# -------- DETALHE POR ID --------
@router.get("/epis/{epi_id}", response_model=schemas.EPIOut)
def obter_epi(epi_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    obj = db.get(EPI, epi_id)
    if not obj:
        raise HTTPException(status_code=404, detail="EPI não encontrado")
    return obj


@router.get("/perigos/{perigo_id}", response_model=schemas.PerigoOut)
def obter_perigo(perigo_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    obj = db.get(Perigo, perigo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Perigo não encontrado")
    return obj


def _safe_int(value, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


def _risk_bounds() -> tuple[int, int, int, int]:
    prob = RISK_MATRIX.get("probability", {})
    sev = RISK_MATRIX.get("severity", {})
    prob_min = _safe_int(prob.get("min"), 1)
    prob_max = _safe_int(prob.get("max"), 5)
    sev_min = _safe_int(sev.get("min"), 1)
    sev_max = _safe_int(sev.get("max"), 5)
    return prob_min, prob_max, sev_min, sev_max


def _validate_optional_default(value: int | None, min_value: int, max_value: int, field: str) -> None:
    if value is None:
        return
    if value != 0 and (value < min_value or value > max_value):
        raise validation_error(
            f"Valor deve ser 0 ou entre {min_value} e {max_value}",
            field=field,
        )


@router.patch("/perigos/{perigo_id}", response_model=schemas.PerigoOut)
def atualizar_perigo(
    perigo_id: int,
    payload: schemas.PerigoUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    obj = db.get(Perigo, perigo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Perigo não encontrado")

    prob_min, prob_max, sev_min, sev_max = _risk_bounds()
    _validate_optional_default(payload.default_probability, prob_min, prob_max, "default_probability")
    _validate_optional_default(payload.default_severity, sev_min, sev_max, "default_severity")

    updated = False
    if payload.default_probability is not None:
        obj.default_probability = int(payload.default_probability)
        updated = True
    if payload.default_severity is not None:
        obj.default_severity = int(payload.default_severity)
        updated = True

    if updated:
        db.commit()
        db.refresh(obj)

    return obj
