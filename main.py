from fastapi import FastAPI
from database import engine
from sqlalchemy import text
import models  # IMPORTANTE: garante que os models sejam carregados

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"health": "up"}

@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return {"db": "connected"}
from database import Base, engine

Base.metadata.create_all(bind=engine)
