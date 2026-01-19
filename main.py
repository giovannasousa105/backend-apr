from consolidation.pdf import gerar_pdf_apr
from fastapi.responses import FileResponse
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
from consolidation.ai import gerar_atividades_por_ai

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
# APRs
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
@app.post("/documentos/consolidar/pdf")
def consolidar_documento_pdf(
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

            hashes = gerar_hashes_origem(
                caminho_epis=epis_path,
                caminho_perigos=perigos_path,
            )

            epis = carregar_epis(epis_path)
            perigos = carregar_perigos(perigos_path)

            atividades_lista = gerar_atividades_por_ai(
                perigos=perigos,
                epis=epis,
            )

            atividades = {
                a["atividade_id"]: a
                for a in atividades_lista
            }

            validar_documento(
                atividades=atividades,
                epis=epis,
                perigos=perigos,
            )

            documento_completo = construir_documento(
                atividades=atividades,
                epis=epis,
                perigos=perigos,
                hashes=hashes,
            )

            # 🔑 PEGAR APENAS UM DOCUMENTO PARA PDF
            documento_pdf = documento_completo["documentos"][0]

            pdf_path = os.path.join(tmpdir, "APR.pdf")
            gerar_pdf_apr(
                documento=documento_pdf,
                caminho_saida=pdf_path,
            )

            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename="APR.pdf",
            )

    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erro na geração do PDF: {str(e)}",
        )
