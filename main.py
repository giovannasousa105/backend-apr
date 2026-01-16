from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import shutil

from database import SessionLocal
import models, schemas

# IMPORTA A FUNÇÃO MULTI-APR (novo nome, mas sem quebrar nada)
from importar_excel import importar_apr_excel

app = FastAPI()


# -------------------------
# DEPENDÊNCIA DO BANCO
# -------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {"status": "ok"}


# -------------------------
# APRs
# -------------------------
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


@app.get("/aprs", response_model=list[schemas.APRResponse])
def listar_aprs(db: Session = Depends(get_db)):
    return db.query(models.APR).all()


# -------------------------
# IMPORTAÇÃO EXCEL (MULTI-APR)
# -------------------------
apr = importar_apr_excel(caminho, db)
def importar_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .xlsx")

    caminho = f"temp_{file.filename}"

    try:
        with open(caminho, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        aprs = importar_aprs_excel(caminho, db)

        return {
            "quantidade_aprs": len(aprs),
            "aprs": aprs
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        file.file.close()
