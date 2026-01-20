from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

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
    try:
        apr = models.APR(
            titulo=payload.titulo,
            risco=payload.risco,
            descricao=payload.descricao,
        )
        db.add(apr)
        db.commit()
        db.refresh(apr)
        return apr
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[schemas.APRResponse])
def listar_aprs(db: Session = Depends(get_db)):
    try:
        return db.query(models.APR).order_by(models.APR.id.desc()).all()
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{apr_id}", response_model=schemas.APRResponseComPassos)
def obter_apr(apr_id: int, db: Session = Depends(get_db)):
    try:
        apr = (
            db.query(models.APR)
            .options(joinedload(models.APR.passos))
            .filter(models.APR.id == apr_id)
            .first()
        )
        if not apr:
            raise HTTPException(status_code=404, detail="APR não encontrada")
        return apr
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{apr_id}/passos", response_model=schemas.APRResponseComPassos)
def adicionar_passo(apr_id: int, payload: schemas.PassoCreate, db: Session = Depends(get_db)):
    try:
        apr = db.query(models.APR).filter(models.APR.id == apr_id).first()
        if not apr:
            raise HTTPException(status_code=404, detail="APR não encontrada")

        passo = models.Passo(
            apr_id=apr_id,
            ordem=payload.ordem,
            descricao=payload.descricao,
            perigos=",".join(payload.perigos or []),
            riscos=payload.riscos or "",
            medidas_controle=payload.medidas_controle or "",
            epis=",".join(payload.epis or []),
            normas=payload.normas or "",
        )
        db.add(passo)
        db.commit()

        apr = (
            db.query(models.APR)
            .options(joinedload(models.APR.passos))
            .filter(models.APR.id == apr_id)
            .first()
        )
        return apr
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
