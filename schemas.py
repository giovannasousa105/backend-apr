from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# -------------------------
# PASSO
# -------------------------
class PassoBase(BaseModel):
    ordem: int
    descricao: str
    perigos: str
    riscos: str
    medidas_controle: str
    epis: str
    normas: str


class PassoCreate(PassoBase):
    pass


class PassoResponse(PassoBase):
    id: int
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


# -------------------------
# APR
# -------------------------
class APRBase(BaseModel):
    titulo: str
    risco: str
    descricao: Optional[str] = None
    status: str


class APRCreate(APRBase):
    passos: List[PassoCreate] = []


class APRResponse(APRBase):
    id: int
    criado_em: datetime
    atualizado_em: datetime
    passos: List[PassoResponse] = []

    class Config:
        from_attributes = True
