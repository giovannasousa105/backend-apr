from fastapi import FastAPI
from routes.importacao import router as import_router

app = FastAPI(title="APR Backend")

app.include_router(import_router)

@app.get("/health")
def health():
    return {"status": "ok"}
