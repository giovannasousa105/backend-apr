from pydantic import BaseModel
from typing import Optional, List

# ---------- APR ----------

class APRBase(BaseModel):
    titulo: str
    risco: str
    descricao: Optional[str] = None


class APRCreate(APRBase):
    pass


# ---------- PASSO ----------

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
    apr_id: int

    class Config:
        from_attributes = True


# ---------- APR RESPONSE (com passos) ----------

class APRResponse(APRBase):
    id: int
    passos: List[PassoResponse] = []

    class Config:
        from_attributes = True


# ---------- USUARIO ----------

class UsuarioBase(BaseModel):
    nome: str
    email: str
    ativo: bool = True
    administrador: bool = False


class UsuarioCreate(UsuarioBase):
    senha: str


class UsuarioResponse(UsuarioBase):
    id: int

    class Config:
        from_attributes = True
