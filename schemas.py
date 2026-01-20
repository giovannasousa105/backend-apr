from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# =========================
# PASSO
# =========================

class PassoCreate(BaseModel):
    ordem: int
    descricao: str
    perigos: Optional[List[str]] = []
    riscos: Optional[str] = ""
    medidas_controle: Optional[str] = ""
    epis: Optional[List[str]] = []
    normas: Optional[str] = ""


class PassoResponse(BaseModel):
    id: int
    apr_id: int
    ordem: int
    descricao: str
    perigos: str
    riscos: str
    medidas_controle: str
    epis: str
    normas: str
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


# =========================
# APR
# =========================

class APRCreate(BaseModel):
    titulo: str
    risco: str
    descricao: Optional[str] = None


class APRUpdate(BaseModel):
    titulo: Optional[str] = None
    risco: Optional[str] = None
    descricao: Optional[str] = None
    status: Optional[str] = None


class APRResponse(BaseModel):
    id: int
    titulo: str
    risco: str
    descricao: Optional[str] = None
    status: str
    criado_em: datetime
    atualizado_em: datetime
    passos: List[PassoResponse] = []

    class Config:
        from_attributes = True


class APRListResponse(BaseModel):
    aprs: List[APRResponse]
