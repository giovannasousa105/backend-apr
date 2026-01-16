from fastapi import FastAPI
from database import SessionLocal

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}
