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
