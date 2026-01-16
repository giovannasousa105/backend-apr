from pydantic import BaseModel
from typing import Optional, List


class PassoBase(BaseModel):
    descricao: str


class PassoResponse(PassoBase):
    id: int

    class Config:
        from_attributes = True


class APRBase(BaseModel):
    titulo: str
    risco: str
    descricao: Optional[str] = None


class APRCreate(APRBase):
    pass


class APRResponse(APRBase):
    id: int
    passos: List[PassoResponse] = []

    class Config:
        from_attributes = True
