from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import SessionLocal
from models import EPI, Perigo
import schemas
from auth import get_current_user

router = APIRouter(tags=["Listagem"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/epis", response_model=list[schemas.EPIOut])
def listar_epis(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    limit = min(max(limit, 1), 200)
    stmt = select(EPI).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/perigos", response_model=list[schemas.PerigoOut])
def listar_perigos(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    limit = min(max(limit, 1), 200)
    stmt = select(Perigo).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()
