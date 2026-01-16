from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class APRCreate(BaseModel):
    titulo: str
    risco: str
    descricao: str | None = None

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/aprs")
def criar_apr(apr: APRCreate):
    return {
        "titulo": apr.titulo,
        "risco": apr.risco,
        "descricao": apr.descricao
    }
