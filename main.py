from fastapi import FastAPI
from database import SessionLocal
import models
import schemas
from importar_excel import importar_apr_excel


app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}
