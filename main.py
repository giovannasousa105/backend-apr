from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import tempfile
import shutil
import os

from consolidation.pdf import gerar_pdf_apr
from consolidation.loader import carregar_epis, carregar_perigos
from consolidation.validator import validar_documento, ValidationError
from consolidation.hasher import gerar_hashes_origem
from consolidation.builder import construir_documento
from consolidation.ai import gerar_atividades_por_ai

from database import SessionLocal
import models
import schemas

app = FastAPI()


# =============================
# NORMALIZAÇÃO DA IA
# =============================
def normalizar_atividades_ai(atividades):
    if not atividades:
        return []

    if isinstance(atividades, dict):
        return [atividades]

    if isinstance(atividades, list):
        return [a for a in atividades if isinstance(a, dict)]

    return []


# =============================
# HEALTH / ROOT
# =============================
@app.get("/health")
def health():
    return {"ok": True}


@app.get("/")
def root():
    return {"status": "ok"}


# =============================
# DB
# =============================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================
# DOCUMENTOS — PDF
# =============================
@app.post("/documentos/consolidar/pdf")
def consolidar_documento_pdf(
    epis_file: UploadFile = File(...),
    perigos_file: UploadFile = File(...),
):
    tmpdir = tempfile.mkdtemp()

    try:
        # -----------------------------
        # SALVAR ARQUIVOS
        # -----------------------------
        epis_path = os.path.join(tmpdir, epis_file.filename)
        perigos_path = os.path.join(tmpdir, perigos_file.filename)

        with open(epis_path, "wb") as f:
            shutil.copyfileobj(epis_file.file, f)

        with open(perigos_path, "wb") as f:
            shutil.copyfileobj(perigos_file.file, f)

        # -----------------------------
        # PIPELINE
        # -----------------------------
        hashes = gerar_hashes_origem(
            caminho_epis=epis_path,
            caminho_perigos=perigos_path,
        )

        epis = carregar_epis(epis_path)        # LISTA
        perigos = carregar_perigos(perigos_path)  # LISTA

        atividades_raw = gerar_atividades_por_ai(
            perigos=perigos,
            epis=epis,
        )

        atividades_lista = normalizar_atividades_ai(atividades_raw)

        atividades = {
            a.get("atividade_id", idx): a
            for idx, a in enumerate(atividades_lista)
        }

        validar_documento(
            atividades=list(atividades.values()),
            epis=epis,
            perigos=perigos,
        )

        documento = construir_documento(
            atividades=atividades,
            epis=epis,
            perigos=perigos,
            hashes=hashes,
        )

        pdf_path = os.path.join(tmpdir, "APR.pdf")

        gerar_pdf_apr(
            documento=documento["documentos"][0],
            caminho_saida=pdf_path,
        )

        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename="APR.pdf",
        )

    except ValidationError as ve:
        pdf_path = os.path.join(tmpdir, "APR_ERRO_VALIDACAO.pdf")

        gerar_pdf_apr(
            documento={"erro": "Erro de validação", "detalhes": str(ve)},
            caminho_saida=pdf_path,
        )

        return FileResponse(pdf_path, filename="APR_ERRO_VALIDACAO.pdf")

    except Exception as e:
        pdf_path = os.path.join(tmpdir, "APR_ERRO.pdf")

        gerar_pdf_apr(
            documento={"erro": "Erro inesperado", "detalhes": str(e)},
            caminho_saida=pdf_path,
        )

        return FileResponse(pdf_path, filename="APR_ERRO.pdf")
