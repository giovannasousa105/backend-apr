from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import APR, Passo
from schemas import APRResponse, PassoBase

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/aprs", response_model=list[APRResponse])
def listar_aprs(db: Session = Depends(get_db)):
    return db.query(APR).all()


@app.get("/aprs/{apr_id}", response_model=APRResponse)
def obter_apr(apr_id: int, db: Session = Depends(get_db)):
    apr = db.query(APR).filter(APR.id == apr_id).first()
    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")
    return apr


@app.post("/aprs/{apr_id}/passos", response_model=dict)
def adicionar_passo(
    apr_id: int,
    passo: PassoBase,
    db: Session = Depends(get_db),
):
    apr = db.query(APR).filter(APR.id == apr_id).first()
    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")

    novo_passo = Passo(apr_id=apr_id, **passo.dict())
    db.add(novo_passo)
    db.commit()

    return {"status": "passo adicionado"}
