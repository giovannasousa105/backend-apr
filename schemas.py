from pydantic import BaseModel
from typing import Optional


class APRCreate(BaseModel):
    titulo: str
    risco: str
    descricao: Optional[str] = None

class APRResponse(APRCreate):
    id: int

    class Config:
        from_attributes = True
class PassoCreate(BaseModel):
    ordem: int
    descricao: str
    perigos: str
    riscos: str
    medidas_controle: str
    epis: str
    normas: str

class PassoResponse(PassoCreate):
    id: int

    class Config:
        from_attributes = True