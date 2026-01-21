from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import tempfile
import shutil
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
def importar_epis_endpoint(file: UploadFile = File(...), db=Depends(get_db)):
    os.makedirs("uploads", exist_ok=True)
    path = os.path.join("uploads", file.filename)

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return importar_epis(db, path)

@router.post("/perigos")
def importar_perigos_endpoint(file: UploadFile = File(...), db=Depends(get_db)):
    os.makedirs("uploads", exist_ok=True)
    path = os.path.join("uploads", file.filename)

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return importar_perigos(db, path)