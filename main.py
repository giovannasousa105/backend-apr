from fastapi import FastAPI, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import tempfile
import os
import shutil

from consolidation.loader import (
    carregar_epis,
    carregar_perigos,
    construir_atividades,
)

from database import SessionLocal
import models
import schemas

app = FastAPI()


# ==================================================
# DB
# ==================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================================================
# ROOT
# ==================================================

@app.get("/")
def root():
    return {"status": "ok"}


# ==================================================
# APRs (CRUD simples)
# ==================================================

@app.get("/aprs", response_model=list[schemas.APRResponse])
def listar_aprs(db: Session = next(get_db())):
    return db.query(models.APR).all()


@app.post("/aprs", response_model=schemas.APRResponse)
def criar_apr(apr: schemas.APRCreate, db: Session = next(get_db())):
    nova_apr = models.APR(
        titulo=apr.titulo,
        risco=apr.risco,
        descricao=apr.descricao,
    )
    db.add(nova_apr)
    db.commit()
    db.refresh(nova_apr)
    return nova_apr


# ==================================================
# DOCUMENTOS — CONSOLIDAÇÃO FINAL
# ==================================================

@app.post("/documentos/consolidar")
def consolidar_documento(
    epis_file: UploadFile = File(...),
    perigos_file: UploadFile = File(...),
):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            epis_path = os.path.join(tmpdir, epis_file.filename)
            perigos_path = os.path.join(tmpdir, perigos_file.filename)

            with open(epis_path, "wb") as f:
                shutil.copyfileobj(epis_file.file, f)

            with open(perigos_path, "wb") as f:
                shutil.copyfileobj(perigos_file.file, f)

            # Loader
            epis = carregar_epis(epis_path)
            perigos = carregar_perigos(perigos_path)

            if not epis:
                raise ValueError("Nenhum EPI carregado")

            if not perigos:
                raise ValueError("Nenhum perigo carregado")

            # Builder automático
            atividades = construir_atividades(perigos, epis)

            documento = {
                "metadados": {
                    "versao": "1.0",
                    "origem": "excel_validado",
                    "status": "consolidado",
                },
                "epis": list(epis.values()),
                "perigos": list(perigos.values()),
                "atividades": atividades,
            }

            return documento

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
