from pydantic import BaseModel
from typing import Optional, List

# ---------- PASSO ----------

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

    class Config:
        orm_mode = True


# ---------- APR ----------

class APRResponse(BaseModel):
    id: int
    titulo: str
    risco: str
    descricao: Optional[str] = None
    passos: List[PassoResponse] = []

    class Config:
        orm_mode = True
