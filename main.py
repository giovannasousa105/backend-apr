from schemas import PassoCreate
from models import Passo, APR
from database import SessionLocal
from fastapi import HTTPException

@app.post("/aprs/{apr_id}/passos")
def adicionar_passo(apr_id: int, passo: PassoCreate):
    db = SessionLocal()

    apr = db.query(APR).filter(APR.id == apr_id).first()
    if not apr:
        raise HTTPException(status_code=404, detail="APR não encontrada")

    novo_passo = Passo(
        atividade_id=apr_id,
        ordem=passo.ordem,
        descricao=passo.descricao,
        perigos=passo.perigos,
        riscos=passo.riscos,
        medidas_controle=passo.medidas_controle,
        epis=passo.epis,
        normas=passo.normas,
    )

    db.add(novo_passo)
    db.commit()
    db.refresh(novo_passo)

    return novo_passo
