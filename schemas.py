from typing import List, Optional
from pydantic import BaseModel


class PassoBase(BaseModel):
    ordem: int
    descricao: str
    perigos: str
    riscos: str
    medidas_controle: str
    epis: str
    normas: str


class PassoResponse(PassoBase):
    id: int

    class Config:
        orm_mode = True


class APRBase(BaseModel):
    titulo: str
    descricao: Optional[str]
    risco: str


class APRResponse(APRBase):
    id: int
    passos: List[PassoResponse] = []

    class Config:
        orm_mode = True
