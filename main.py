import schemas
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import Base, engine, SessionLocal
import models
from importar_excel import importar_apr_excel

# 🔴 CRIA O APP
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


# 🔹 LISTAR APRS (COM PASSOS)
@app.get("/aprs")
def listar_aprs(db: Session = Depends(get_db)):
    aprs = (
        db.query(models.APR)
        .options(joinedload(models.APR.passos))
        .all()
    )
    return aprs


# 🔹 CRIAR APR
@app.post("/aprs", response_model=schemas.APRResponse)
def criar_apr(
    apr: schemas.APRCreate,
    db: Session = Depends(get_db)
):
    novo_apr = models.APR(
        titulo=apr.titulo,
        risco=apr.risco,
        descricao=apr.descricao
    )
    db.add(novo_apr)
    db.commit()
    db.refresh(novo_apr)
    return novo_apr

# 🔹 OBTER APR COM PASSOS
@app.get("/aprs/{apr_id}")
def obter_apr(apr_id: int, db: Session = Depends(get_db)):
    apr = (
        db.query(models.APR)
        .options(joinedload(models.APR.passos))
        .filter(models.APR.id == apr_id)
        .first()
    )

    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")

    return apr


# 🔹 ADICIONAR PASSO
@app.post(
    "/aprs/{apr_id}/passos",
    response_model=schemas.PassoResponse
)
def adicionar_passo(
    apr_id: int,
    passo: schemas.PassoCreate,
    db: Session = Depends(get_db)
):
    apr = db.query(models.APR).filter(models.APR.id == apr_id).first()
    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")

    novo_passo = models.Passo(
        apr_id=apr_id,
        ordem=passo.ordem,
        descricao=passo.descricao,
        perigos=passo.perigos,
        riscos=passo.riscos,
        medidas_controle=passo.medidas_controle,
        epis=passo.epis,
        normas=passo.normas
    )

    db.add(novo_passo)
    db.commit()
    db.refresh(novo_passo)
    return novo_passo

# 🔹 LISTAR PASSOS DE UMA APR
@app.get("/aprs/{apr_id}/passos")
def listar_passos(apr_id: int, db: Session = Depends(get_db)):
    apr = db.query(models.APR).filter(models.APR.id == apr_id).first()
    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")

    return db.query(models.Passo).filter(models.Passo.apr_id == apr_id).all()


# 🔹 DELETAR APR
@app.delete("/aprs/{apr_id}")
def deletar_apr(apr_id: int, db: Session = Depends(get_db)):
    apr = db.query(models.APR).filter(models.APR.id == apr_id).first()
    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")

    db.delete(apr)
    db.commit()
    return {"detail": "APR deletada com sucesso"}


# 🔹 DELETAR PASSO
@app.delete("/passos/{passo_id}")
def deletar_passo(passo_id: int, db: Session = Depends(get_db)):
    passo = db.query(models.Passo).filter(models.Passo.id == passo_id).first()
    if not passo:
        raise HTTPException(status_code=404, detail="Passo não encontrado")

    db.delete(passo)
    db.commit()
    return {"detail": "Passo deletado com sucesso"}


# 🔹 IMPORTAR APR VIA EXCEL
@app.post("/importar_apr/")
def importar_apr(file_path: str, db: Session = Depends(get_db)):
    apr = importar_apr_excel(file_path, db)
    return apr
