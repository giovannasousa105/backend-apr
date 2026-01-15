from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
import models

# 🔴 CRIA O APP PRIMEIRO
app = FastAPI()

# 🔴 CRIA AS TABELAS
Base.metadata.create_all(bind=engine)

# 🔴 DEPENDÊNCIA DO BANCO
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- ROTAS ----------

@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/aprs")
def listar_aprs(db: Session = Depends(get_db)):
    return db.query(models.APR).all()


@app.post("/aprs")
def criar_apr(
    titulo: str,
    risco: str,
    descricao: str | None = None,
    db: Session = Depends(get_db)
):
    apr = models.APR(
        titulo=titulo,
        risco=risco,
        descricao=descricao
    )
    db.add(apr)
    db.commit()
    db.refresh(apr)
    return apr


@app.post("/aprs/{apr_id}/passos")
def adicionar_passo(
    apr_id: int,
    ordem: int,
    descricao: str,
    perigos: str,
    riscos: str,
    medidas_controle: str,
    epis: str,
    normas: str,
    db: Session = Depends(get_db)
):
    apr = db.query(models.APR).filter(models.APR.id == apr_id).first()
    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")

    passo = models.Passo(
        apr_id=apr_id,
        ordem=ordem,
        descricao=descricao,
        perigos=perigos,
        riscos=riscos,
        medidas_controle=medidas_controle,
        epis=epis,
        normas=normas
    )

    db.add(passo)
    db.commit()
    db.refresh(passo)
    return passo
@app.get("/aprs/{apr_id}/passos")
def listar_passos(apr_id: int, db: Session = Depends(get_db)):  
    apr = db.query(models.APR).filter(models.APR.id == apr_id).first()
    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")
    return db.query(models.Passo).filter(models.Passo.apr_id == apr_id).all()   