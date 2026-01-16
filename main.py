from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import shutil

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


@app.get("/aprs")
def listar_aprs(db: Session = Depends(get_db)):
    return db.query(models.APR).all()


@app.post("/aprs")
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
