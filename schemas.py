from pydantic import BaseModel
from typing import Optional, List   
import schemas as schemas   
from pydantic import BaseModel
from typing import Optional

class APRCreate(BaseModel):
    titulo: str
    risco: str
    descricao: Optional[str] = None


# ---------- APR ----------

class APRBase(BaseModel):
    titulo: str
    risco: str
    descricao: Optional[str] = None


class APRCreate(APRBase):
    pass


class APRResponse(APRBase):
    id: int

    class Config:
        from_attributes = True


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
        from_attributes = True


class APRResponse(BaseModel):
    id: int
    titulo: str
    risco: str
    descricao: str | None
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
# ---------- FIM USUARIO ----------
