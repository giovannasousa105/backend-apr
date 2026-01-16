from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import shutil
from fastapi import UploadFile, File
import shutil
import os

from consolidation.loader import (
    carregar_atividades_passos,
    carregar_epis,
    carregar_perigos,
)
from consolidation.validator import validar_documento, ValidationError
from consolidation.hasher import gerar_hashes_origem
from consolidation.builder import construir_documento
from database import SessionLocal
import models
import schemas
from importar_excel import importar_apr_excel

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/aprs", response_model=list[schemas.APRResponse])
def listar_aprs(db: Session = Depends(get_db)):
    return db.query(models.APR).all()

@app.post("/aprs", response_model=schemas.APRResponse)
def criar_apr(apr: schemas.APRCreate, db: Session = Depends(get_db)):
    nova_apr = models.APR(
        titulo=apr.titulo,
        risco=apr.risco,
        descricao=apr.descricao
    )
    db.add(nova_apr)
    db.commit()
    db.refresh(nova_apr)
    return nova_apr

# 🔴 ENDPOINT DE IMPORTAÇÃO (ADICIONAR AGORA)
@app.post("/aprs/importar-excel")
def importar_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .xlsx")

    caminho = f"/tmp/{file.filename}"

    try:
        with open(caminho, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        apr = importar_apr_excel(caminho, db)

        return {
            "status": "ok",
            "apr_id": apr.id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        file.file.close()

@app.get("/aprs/{apr_id}", response_model=schemas.APRResponse)
def obter_apr(apr_id: int, db: Session = Depends(get_db)):
    apr = db.query(models.APR).filter(models.APR.id == apr_id).first()
    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")
    return apr
@app.post("/documentos/consolidar")
def consolidar_documento(
    atividades_file: UploadFile = File(...),
    epis_file: UploadFile = File(...),
    perigos_file: UploadFile = File(...),
):
    # Pasta temporária segura
    base_path = "/tmp"

    atividades_path = os.path.join(base_path, atividades_file.filename)
    epis_path = os.path.join(base_path, epis_file.filename)
    perigos_path = os.path.join(base_path, perigos_file.filename)

    try:
        # Salvar arquivos
        with open(atividades_path, "wb") as f:
            shutil.copyfileobj(atividades_file.file, f)

        with open(epis_path, "wb") as f:
            shutil.copyfileobj(epis_file.file, f)

        with open(perigos_path, "wb") as f:
            shutil.copyfileobj(perigos_file.file, f)

        # 1️⃣ Hashes (auditoria)
        hashes = gerar_hashes_origem(
            caminho_atividades=atividades_path,
            caminho_epis=epis_path,
            caminho_perigos=perigos_path
        )

        # 2️⃣ Loader
        atividades = carregar_atividades_passos(atividades_path)
        epis = carregar_epis(epis_path)
        perigos = carregar_perigos(perigos_path)

        # 3️⃣ Validator (engenharia)
        validar_documento(
            atividades=atividades,
            epis=epis,
            perigos=perigos
        )

        # 4️⃣ Builder (verdade técnica)
        documento = construir_documento(
            atividades=atividades,
            epis=epis,
            perigos=perigos,
            hashes=hashes
        )

        return {
            "status": "consolidado",
            "hashes": hashes,
            "documento_preview": documento
        }

    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro na consolidação: {str(e)}")

    finally:
        atividades_file.file.close()
        epis_file.file.close()
        perigos_file.file.close()
