from fastapi import FastAPI
from database import Base, engine
import models  # registra tabelas
from routes.apr import router as apr_router

app = FastAPI(title="APR API")


@app.on_event("startup")
def startup():
    # garante criação das tabelas no boot
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "alive"}


# ativa endpoints /aprs
app.include_router(apr_router)
