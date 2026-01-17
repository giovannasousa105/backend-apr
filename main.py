from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import tempfile
import shutil
import os

from consolidation.loader import (
    carregar_epis,
    carregar_perigos,
)

from consolidation.validator import validar_documento, ValidationError
from consolidation.hasher import gerar_hashes_origem
from consolidation.builder import construir_documento

from database import SessionLocal
import models
import schemas

# 🔹 função isolada (OpenAI depois)
from consolidation.ai import gerar_atividades_por_ai

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
# APRs (mantido igual)
# ==================================================

@app.get("/aprs", response_model=list[schemas.APRResponse])
def listar_aprs(db: Session = Depends(get_db)):
    return db.query(models.APR).all()


@app.post("/aprs", response_model=schemas.APRResponse)
def criar_apr(apr: schemas.APRCreate, db: Session = Depends(get_db)):
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
# DOCUMENTOS — CONSOLIDAÇÃO
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

            # 1️⃣ Hash (auditoria preservada)
            hashes = gerar_hashes_origem(
                caminho_epis=epis_path,
                caminho_perigos=perigos_path,
            )

            # 2️⃣ Loader (somente cadastros)
            epis = carregar_epis(epis_path)
            perigos = carregar_perigos(perigos_path)

            if not epis:
                raise ValueError("Nenhum EPI carregado")
            if not perigos:
                raise ValueError("Nenhum perigo carregado")

            # 3️⃣ OpenAI gera atividades/passos
            atividades = gerar_atividades_por_ai(
                perigos=perigos,
                epis=epis
            )

            # 4️⃣ Validator (engenharia / NR)
            validar_documento(
                atividades=atividades,
                epis=epis,
                perigos=perigos
            )

            # 5️⃣ Builder (verdade técnica)
            documento = construir_documento(
                atividades=atividades,
                epis=epis,
                perigos=perigos,
                hashes=hashes
            )

            return {
                "status": "consolidado",
                "hashes": hashes,
                "documento": documento
            }

    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erro na consolidação: {str(e)}"
        )
