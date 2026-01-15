from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
from models import APR, Passo

Base.metadata.create_all(bind=engine)

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


# =====================
# APRs
# =====================

@app.post("/aprs")
def criar_apr(
    titulo: str,
    risco: str,
    descricao: str | None = None,
    db: Session = Depends(get_db)
):
    apr = APR(
        titulo=titulo,
        risco=risco,
        descricao=descricao
    )
    db.add(apr)
    db.commit()
    db.refresh(apr)
    return apr


@app.get("/aprs")
def listar_aprs(db: Session = Depends(get_db)):
    return db.query(APR).all()


# =====================
# PASSOS DA APR
# =====================

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
    apr = db.query(APR).filter(APR.id == apr_id).first()

    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")

    passo = Passo(
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
