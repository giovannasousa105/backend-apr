# ✅ MODO CODEX (resposta 100% código)
# Objetivo:
# 1) Voltar o POST /aprs (criar APR) + GETs necessários
# 2) Matar de vez o erro: "'list' object has no attribute 'keys'"
# 3) Manter compatível com seu projeto (SQLAlchemy + FastAPI)

# ============================================================
# 1) consolidation/utils.py  (CRIAR ESTE ARQUIVO)
# ============================================================

from typing import Any, Dict


def garantir_dict(atividades: Any) -> Dict[str, Any]:
    """
    Garante que atividades SEMPRE seja dict antes de qualquer .keys().
    - dict -> retorna
    - list -> converte para {"1": item1, "2": item2, ...}
    - None/other -> fallback safe
    """
    if atividades is None:
        return {}

    if isinstance(atividades, dict):
        return atividades

    if isinstance(atividades, list):
        out: Dict[str, Any] = {}
        for i, item in enumerate(atividades, start=1):
            out[str(i)] = item
        return out

    return {"1": {"atividade": str(atividades), "passos": []}}


# ============================================================
# 2) consolidation/builder.py  (PATCH — adicione no topo)
#    >>> aqui é onde geralmente estoura .keys()
# ============================================================

from consolidation.utils import garantir_dict

# ... dentro da função que recebe "atividades" e antes de usar .keys():
# atividades = garantir_dict(atividades)

# EXEMPLO (ajuste para o seu builder real):
def construir_documento(atividades, *args, **kwargs):
    atividades = garantir_dict(atividades)  # 🔥 FIX DO .keys()

    # agora pode usar atividades.keys() sem explodir
    # ... seu código atual ...
    documento = {"atividades": list(atividades.values())}  # exemplo
    return documento


# ============================================================
# 3) schemas.py  (CRIAR/ATUALIZAR)
# ============================================================

from typing import List, Optional
from pydantic import BaseModel


class PassoCreate(BaseModel):
    ordem: int
    descricao: str
    perigos: Optional[List[str]] = []
    riscos: Optional[str] = ""
    medidas_controle: Optional[str] = ""
    epis: Optional[List[str]] = []
    normas: Optional[str] = ""


class APRCreate(BaseModel):
    titulo: str
    risco: str
    descricao: Optional[str] = None


class PassoResponse(BaseModel):
    id: int
    ordem: int
    descricao: str
    perigos: str
    riscos: str
    medidas_controle: str
    epis: str
    normas: str

    class Config:
        from_attributes = True


class APRResponse(BaseModel):
    id: int
    titulo: str
    risco: str
    descricao: Optional[str] = None
    passos: List[PassoResponse] = []

    class Config:
        from_attributes = True


# ============================================================
# 4) models.py  (GARANTA QUE ESTÁ ASSIM — ou atualize)
# ============================================================

from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class APR(Base):
    __tablename__ = "aprs"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    risco = Column(String(50), nullable=False)
    descricao = Column(Text, nullable=True)

    passos = relationship(
        "Passo",
        back_populates="apr",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Passo(Base):
    __tablename__ = "passos"

    id = Column(Integer, primary_key=True, index=True)
    apr_id = Column(Integer, ForeignKey("aprs.id"), nullable=False)

    ordem = Column(Integer, nullable=False)
    descricao = Column(Text, nullable=False)
    perigos = Column(Text, nullable=False, default="")
    riscos = Column(Text, nullable=False, default="")
    medidas_controle = Column(Text, nullable=False, default="")
    epis = Column(Text, nullable=False, default="")
    normas = Column(Text, nullable=False, default="")

    apr = relationship("APR", back_populates="passos")


# ============================================================
# 5) routes/apr.py  (CRIAR ESTE ROUTER)
# ============================================================

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
    apr = models.APR(
        titulo=payload.titulo,
        risco=payload.risco,
        descricao=payload.descricao,
    )
    db.add(apr)
    db.commit()
    db.refresh(apr)
    return apr


@router.get("", response_model=list[schemas.APRResponse])
def listar_aprs(db: Session = Depends(get_db)):
    aprs = (
        db.query(models.APR)
        .options(joinedload(models.APR.passos))
        .order_by(models.APR.id.desc())
        .all()
    )
    return aprs


@router.get("/{apr_id}", response_model=schemas.APRResponse)
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


@router.post("/{apr_id}/passos", response_model=schemas.APRResponse)
def adicionar_passo(apr_id: int, payload: schemas.PassoCreate, db: Session = Depends(get_db)):
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


# ============================================================
# 6) main.py  (GARANTA QUE INCLUI O ROUTER)
# ============================================================

from fastapi import FastAPI
from database import Base, engine
from routes.apr import router as apr_router

app = FastAPI(title="APR API")

# cria tabelas
Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "alive"}

# ✅ VOLTOU: POST /aprs + GET /aprs + GET /aprs/{id} + POST /aprs/{id}/passos
app.include_router(apr_router)


# ============================================================
# 7) COMMIT + DEPLOY
# ============================================================

# git add consolidation/utils.py consolidation/builder.py schemas.py models.py routes/apr.py main.py
# git commit -m "fix: normalizar atividades para evitar .keys() em list + restore CRUD APR endpoints"
# git push origin main
