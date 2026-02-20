from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import shutil
import logging
from uuid import uuid4

from database import SessionLocal
from importar_excel import importar_epis, importar_perigos
from auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import", tags=["Importacao"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _save_upload(file: UploadFile) -> str:
    os.makedirs("uploads", exist_ok=True)

    filename = os.path.basename(file.filename or "upload.xlsx")
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Arquivo deve ser .xlsx ou .xls")

    unique_name = f"{uuid4().hex}{ext}"
    path = os.path.join("uploads", unique_name)

    try:
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    return path


def _cleanup_upload(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        logger.warning("Falha ao remover upload temporario: %s", path)


@router.post("/epis")
def importar_epis_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    path = _save_upload(file)
    try:
        return importar_epis(db, path)
    except ValueError as exc:
        logger.info("Contrato de Excel invalido (EPIs): %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Erro ao importar EPIs")
        raise HTTPException(status_code=500, detail="Falha ao importar EPIs")
    finally:
        _cleanup_upload(path)


@router.post("/perigos")
def importar_perigos_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    path = _save_upload(file)
    try:
        return importar_perigos(db, path)
    except ValueError as exc:
        logger.info("Contrato de Excel invalido (perigos): %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Erro ao importar perigos")
        raise HTTPException(status_code=500, detail="Falha ao importar perigos")
    finally:
        _cleanup_upload(path)
