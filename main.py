from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import shutil

from database import SessionLocal
import models
import schemas
from importar_excel import importar_aprs_excel

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
@app.post("/aprs/importar-excel-multi")
def importar_excel_multi(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .xlsx")

    caminho = f"/tmp/{file.filename}"

    try:
        with open(caminho, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        aprs = importar_aprs_excel(caminho, db)

        return {
            "status": "ok",
            "quantidade_aprs": len(aprs),
            "ids_aprs": [apr.id for apr in aprs]
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
