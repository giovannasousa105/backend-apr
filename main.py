from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/aprs")
def criar_apr():
    return {"msg": "rota aprs funcionando"}
