import os
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from env_loader import load_environment
load_environment()

from database import Base, SessionLocal, engine
from sqlalchemy import select
from excel_contract import get_contract_cached
from importar_excel import importar_epis, importar_perigos
from routes.importacao import router as import_router
from routes.listagem import router as list_router
from routes.v1 import router as v1_router
from routes.aprs import router as aprs_router
from routes.apr_mvp import router as apr_mvp_router
from routes.activities import router as activities_router
from routes.shares import router as shares_router
from routes.legacy_apr import router as legacy_apr_router
from routes.auth import router as auth_router
from routes.companies import router as companies_router
from routes.invites import router as invites_router
from routes.admin_ui import router as admin_ui_router
from routes.account import router as account_router
from routes.seller_activation import router as seller_activation_router
from api_errors import ApiError
from auth_utils import hash_password, generate_token
from models import User, Company

class JSONCharsetMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                content_type = None
                for key, value in headers:
                    if key.lower() == b"content-type":
                        content_type = value.decode("latin-1")
                        break

                if content_type is None or content_type.lower().startswith("application/json"):
                    if content_type is None or "charset" not in content_type.lower():
                        headers = [(k, v) for (k, v) in headers if k.lower() != b"content-type"]
                        headers.append((b"content-type", b"application/json; charset=utf-8"))
                        message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid4().hex
        method = scope.get("method", "-")
        path = scope.get("path", "-")
        status_code = 500
        started = time.perf_counter()

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 500))
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("utf-8")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            latency_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "request method=%s path=%s status=%s latency_ms=%.2f request_id=%s",
                method,
                path,
                status_code,
                latency_ms,
                request_id,
            )

app = FastAPI(title="APR Backend")

def _parse_csv_env(env_name: str) -> list[str]:
    raw = os.getenv(env_name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


default_cors_origins = [
    "http://localhost:50000",
    "http://127.0.0.1:50000",
]

cors_origins = _parse_csv_env("CORS_ORIGINS") or default_cors_origins
cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", "").strip() or None
cors_allow_all = os.getenv("CORS_ALLOW_ALL", "false").lower() in {"1", "true", "yes"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if cors_allow_all else cors_origins,
    allow_origin_regex=None if cors_allow_all else cors_origin_regex,
    allow_credentials=not cors_allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(JSONCharsetMiddleware)
app.add_middleware(RequestLoggingMiddleware)

logger = logging.getLogger(__name__)
APP_VERSION = os.getenv("APP_VERSION", "2026.02.20")

@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors() if hasattr(exc, "errors") else []
    field = None
    message = "Dados invalidos"
    if errors:
        err = errors[0]
        loc = err.get("loc") or []
        parts = [str(p) for p in loc if p not in ("body", "query", "path")]
        if parts:
            field = ".".join(parts)
        message = err.get("msg") or message
    return JSONResponse(
        status_code=422,
        content={"code": "validation_error", "message": message, "field": field},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and {"code", "message", "field"}.issubset(exc.detail.keys()):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    if exc.status_code == 404:
        code = "not_found"
    elif exc.status_code == 409:
        code = "conflict"
    elif exc.status_code == 400:
        code = "bad_request"
    else:
        code = "http_error"

    return JSONResponse(
        status_code=exc.status_code,
        content={"code": code, "message": str(exc.detail), "field": None},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Erro inesperado na API")
    return JSONResponse(
        status_code=500,
        content={"code": "server_error", "message": "Erro interno", "field": None},
    )

app.include_router(import_router)
app.include_router(list_router)
app.include_router(v1_router)
app.include_router(aprs_router)
app.include_router(apr_mvp_router)
app.include_router(seller_activation_router)
app.include_router(account_router)
app.include_router(activities_router)
app.include_router(shares_router)
app.include_router(legacy_apr_router)
app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(invites_router)
app.include_router(admin_ui_router)

@app.get("/contract")
def contract_legacy(request: Request):
    # Compat: endpoint legado sem prefixo /v1
    contract, headers, not_modified = get_contract_cached(request.headers)
    if not_modified:
        return Response(status_code=304, headers=headers)
    return JSONResponse(content=contract, headers=headers)


@app.get("/schema")
def schema_legacy(request: Request):
    # Compat: endpoint legado sem prefixo /v1
    contract, headers, not_modified = get_contract_cached(request.headers)
    if not_modified:
        return Response(status_code=304, headers=headers)
    return JSONResponse(content=contract, headers=headers)

@app.on_event("startup")
def seed_from_xlsx() -> None:
    base_dir = os.path.dirname(__file__)
    epi_path = os.path.join(base_dir, "epis_apr_modelo_validado.xlsx")
    perigo_path = os.path.join(base_dir, "perigos_apr_modelo_validado.xlsx")

    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)

        if os.path.exists(epi_path):
            importar_epis(db, epi_path)
        else:
            print(f"Seed skip: arquivo nao encontrado: {epi_path}")

        if os.path.exists(perigo_path):
            importar_perigos(db, perigo_path)
        else:
            print(f"Seed skip: arquivo nao encontrado: {perigo_path}")

        admin_email = os.getenv("ADMIN_EMAIL")
        admin_password = os.getenv("ADMIN_PASSWORD")
        admin_company = os.getenv("ADMIN_COMPANY", "Empresa")
        if admin_email and admin_password:
            admin_email = admin_email.lower()
            existing = db.execute(select(User).where(User.email == admin_email)).scalar_one_or_none()
            if not existing:
                company = db.execute(
                    select(Company).where(Company.name == admin_company)
                ).scalar_one_or_none()
                if not company:
                    company = Company(name=admin_company)
                    db.add(company)
                    db.flush()
                user = User(
                    email=admin_email,
                    name="Admin",
                    password_hash=hash_password(admin_password),
                    role="admin",
                    company_id=company.id,
                    api_token=generate_token(),
                    is_active=True,
                )
                db.add(user)
                db.commit()
                print("Seed admin criado:", admin_email)
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "ok", "service": "APR Backend"}


@app.get("/version")
def version():
    return {"service": "APR Backend", "version": APP_VERSION}
