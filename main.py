from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
from models import APR

app = FastAPI()

# cria as tabelas
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


@app.get("/health")
def health():
    return {"health": "up"}


# 🔹 LISTAR APRs
@app.get("/aprs")
def listar_aprs(db: Session = Depends(get_db)):
    return db.query(APR).all()


# 🔹 CRIAR APR
@app.post("/aprs")
def criar_apr(
    titulo: str,
    risco: str,
    descricao: str | None = None,
    db: Session = Depends(get_db),
):
    apr = APR(titulo=titulo, risco=risco, descricao=descricao)
    db.add(apr)
    db.commit()
    db.refresh(apr)
    return apr


# 🔹 DELETAR APR
@app.delete("/aprs/{apr_id}")
def deletar_apr(apr_id: int, db: Session = Depends(get_db)):
    apr = db.query(APR).filter(APR.id == apr_id).first()
    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")

    db.delete(apr)
    db.commit()
    return {"message": "APR removida com sucesso"}
