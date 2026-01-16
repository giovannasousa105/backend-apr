from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database import SessionLocal
import models
import schemas
from importar_excel import importar_apr_excel

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/aprs")
def listar_aprs(db: Session = Depends(get_db)):
    return db.query(models.APR).all()
