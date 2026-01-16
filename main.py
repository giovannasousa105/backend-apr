from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
import models
import schemas

app = FastAPI(title="APR API")


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


@app.get("/aprs/{apr_id}", response_model=schemas.APRResponse)
def obter_apr(apr_id: int, db: Session = Depends(get_db)):
    apr = db.query(models.APR).filter(models.APR.id == apr_id).first()

    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")

    return apr


# -------------------------
# PASSOS
# -------------------------
@app.post("/aprs/{apr_id}/passos", response_model=schemas.PassoResponse)
def criar_passo(
    apr_id: int,
    passo: schemas.PassoCreate,
    db: Session = Depends(get_db)
):
    apr = db.query(models.APR).filter(models.APR.id == apr_id).first()
    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")

    novo_passo = models.Passo(
        descricao=passo.descricao,
        apr_id=apr_id
    )

    db.add(novo_passo)
    db.commit()
    db.refresh(novo_passo)

    return novo_passo
