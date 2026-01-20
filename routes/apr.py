from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from database import SessionLocal

router = APIRouter(prefix="/aprs", tags=["APR"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=schemas.APRResponse)
def criar_apr(payload: schemas.APRCreate, db: Session = Depends(get_db)):
    apr = models.APR(titulo=payload.titulo, risco=payload.risco, descricao=payload.descricao)
    db.add(apr)
    db.commit()
    db.refresh(apr)
    return apr


@router.get("", response_model=list[schemas.APRResponse])
def listar_aprs(db: Session = Depends(get_db)):
    return db.query(models.APR).order_by(models.APR.id.desc()).all()


@router.get("/{apr_id}", response_model=schemas.APRResponseComPassos)
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
