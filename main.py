from fastapi import FastAPI
from database import Base, engine

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"health": "up"}
