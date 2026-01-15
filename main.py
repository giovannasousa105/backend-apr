from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import APR, Passo

app = FastAPI()

Base.metadata.create_all(bind=engine)


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

    try:
        passo = Passo(
            atividade_id=apr_id,   # mantém como está no seu model
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

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
