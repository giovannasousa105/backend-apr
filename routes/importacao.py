from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import tempfile

from database import SessionLocal
from importar_excel import importar_epis, importar_perigos

router = APIRouter(prefix="/import", tags=["Importação"])


# -------------------------
# Dependência de banco
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# IMPORTAR EPIs
# -------------------------
@router.post("/epis")
async def importar_epis_route(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .xlsx")

    with tempfile.TemporaryDirectory() as tmp:
        caminho = os.path.join(tmp, file.filename)
        with open(caminho, "wb") as f:
            f.write(await file.read())

        resultado = importar_epis(db, caminho)
        return {
            "status": "ok",
            "resultado": resultado
        }


# -------------------------
# IMPORTAR PERIGOS
# -------------------------
@router.post("/perigos")
async def importar_perigos_route(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .xlsx")

    with tempfile.TemporaryDirectory() as tmp:
        caminho = os.path.join(tmp, file.filename)
        with open(caminho, "wb") as f:
            f.write(await file.read())

        resultado = importar_perigos(db, caminho)
        return {
            "status": "ok",
            "resultado": resultado
        }
