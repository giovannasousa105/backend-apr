from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from pathlib import Path
import json

from database import SessionLocal
from models import APR, Passo, APRShare, APREvent
from apr_documents import write_apr_pdf, validate_apr_for_pdf, PDF_TEMPLATE_VERSION
from excel_contract import get_excel_hashes
from api_errors import ApiError
from risk_engine import rebuild_risk_items_for_apr, list_risk_items_for_apr
from status_utils import is_final_status


router = APIRouter(tags=["Share"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_event(db: Session, apr_id: int, event: str, payload: dict | None) -> None:
    data = json.dumps(payload, ensure_ascii=False) if payload else None
    apr = db.get(APR, apr_id)
    company_id = apr.company_id if apr else None
    db.add(APREvent(apr_id=apr_id, company_id=company_id, event=event, payload=data))


@router.get("/share/{token}")
def baixar_compartilhado(token: str, db: Session = Depends(get_db)):
    share = db.execute(select(APRShare).where(APRShare.token == token)).scalar_one_or_none()
    if not share:
        raise ApiError(
            status_code=404,
            code="not_found",
            message="Compartilhamento nao encontrado",
            field="token",
        )

    apr = db.get(APR, share.apr_id)
    if not apr:
        raise ApiError(status_code=404, code="not_found", message="APR nao encontrada", field="apr_id")

    if not is_final_status(apr.status):
        raise ApiError(
            status_code=400,
            code="apr_not_final",
            message="APR precisa estar finalizada para gerar PDF",
            field="status",
        )

    base_dir = Path(__file__).resolve().parent.parent
    path = base_dir / "exports" / share.filename

    if not path.exists():
        passos = db.execute(select(Passo).where(Passo.apr_id == share.apr_id)).scalars().all()
        rebuild_risk_items_for_apr(db, share.apr_id)
        db.commit()
        risk_items = list_risk_items_for_apr(db, share.apr_id)
        try:
            validate_apr_for_pdf(apr, passos, risk_items)
        except ApiError:
            raise
        path = write_apr_pdf(apr, passos, share.filename, risk_items)
        if not apr.source_hashes:
            apr.source_hashes = json.dumps(get_excel_hashes(), ensure_ascii=False)
        apr.template_version = PDF_TEMPLATE_VERSION
        db.commit()

    _add_event(db, share.apr_id, "share_accessed", {"token": token})
    db.commit()

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=share.filename,
    )
