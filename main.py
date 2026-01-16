from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
import models, schemas

app = FastAPI()

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"status": "ok"}

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

@app.post("/passos")
def criar_passo(
    ordem: int,
    descricao: str,
    perigos: str,
    riscos: str,
    medidas_controle: str,
    epis: str,
    normas: str,
    db: Session = Depends(get_db)
):
    passo = models.Passo(
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

@app.get("/passos", response_model=list[schemas.PassoResponse])
def listar_passos(db: Session = Depends(get_db)):
    return db.query(models.Passo).all()
